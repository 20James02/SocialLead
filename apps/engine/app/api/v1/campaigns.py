"""Reviewed OA customer-care batches. No automatic sending to personal accounts."""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import DbSession, SessionAuth
from app.api.v1.workspace import require, record_event
from app.infrastructure.database.models import (
    CampaignDB,
    CampaignRecipientDB,
    CustomerDB,
    PermissionDB,
    ConversationDB,
    MessageDB,
)
from app.modules.campaign.consent_manager import consent_governance
from app.modules.crm.care_service import to_utc
from app.integrations.zalo.adapter import zalo_oa
from app.infrastructure.security.vault import vault

router = APIRouter(
    prefix="/campaigns", tags=["OA Care Campaigns"], dependencies=[SessionAuth]
)


class CampaignInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    message_template: str = Field(min_length=1, max_length=2000)
    customer_ids: list[str] = Field(min_length=1, max_length=100)
    frequency_cap_days: int = Field(default=7, ge=1, le=365)


def eligibility(db, campaign, recipient):
    customer = db.get(CustomerDB, recipient.customer_id)
    if not customer or customer.deleted_at:
        return False, "Customer is inactive", None
    ambiguous = (
        db.query(CampaignRecipientDB)
        .filter(
            CampaignRecipientDB.customer_id == customer.id,
            CampaignRecipientDB.status.in_(["SENDING", "UNKNOWN"]),
        )
        .first()
    )
    if ambiguous:
        return False, "Previous delivery is unconfirmed; verify in OA first", None
    if not vault.get_secret("zalo_access_token"):
        return False, "Zalo OA access token is not configured", None
    permission = db.query(PermissionDB).filter_by(person_id=customer.person_id).first()
    last_sent = (
        db.query(CampaignRecipientDB)
        .filter(
            CampaignRecipientDB.customer_id == customer.id,
            CampaignRecipientDB.sent_at.isnot(None),
        )
        .order_by(CampaignRecipientDB.sent_at.desc())
        .first()
    )
    eligible, reason = consent_governance.can_send_campaign(
        permission,
        last_sent.sent_at if last_sent else None,
        campaign.frequency_cap_days,
    )
    if not eligible:
        return False, reason, None
    if not permission.zalo_allowed:
        return False, "Zalo permission is not enabled", None
    conv = (
        db.query(ConversationDB)
        .filter_by(platform="ZALO", linked_person_id=customer.person_id)
        .order_by(ConversationDB.last_message_at.desc())
        .first()
    )
    if not conv or not conv.external_conversation_id.isdigit():
        return False, "Link a conversation using the official Zalo OA user ID", None
    inbound = (
        db.query(MessageDB)
        .filter_by(conversation_id=conv.id, sender_type="CUSTOMER")
        .order_by(MessageDB.sent_at.desc())
        .first()
    )
    if not inbound or to_utc(inbound.sent_at) < datetime.now(timezone.utc) - timedelta(
        days=7
    ):
        return (
            False,
            "OA consultation requires customer interaction within 7 days",
            None,
        )
    return True, "Eligible for reviewed OA consultation", conv


@router.get("")
def list_campaigns(db: Session = DbSession):
    return [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "message_template": c.message_template,
            "frequency_cap_days": c.frequency_cap_days,
        }
        for c in db.query(CampaignDB).order_by(CampaignDB.created_at.desc()).all()
    ]


@router.post("", status_code=201)
def create_campaign(req: CampaignInput, db: Session = DbSession):
    for customer_id in set(req.customer_ids):
        require(db, CustomerDB, customer_id)
    campaign = CampaignDB(
        name=req.name,
        channel="ZALO_OA_CS",
        message_template=req.message_template,
        frequency_cap_days=req.frequency_cap_days,
    )
    db.add(campaign)
    db.flush()
    for customer_id in set(req.customer_ids):
        db.add(CampaignRecipientDB(campaign_id=campaign.id, customer_id=customer_id))
    db.commit()
    return {"id": campaign.id}


@router.get("/{campaign_id}/preview")
def preview_campaign(campaign_id: str, db: Session = DbSession):
    campaign = require(db, CampaignDB, campaign_id)
    result = []
    for r in db.query(CampaignRecipientDB).filter_by(campaign_id=campaign.id):
        eligible, reason, _ = eligibility(db, campaign, r)
        customer = db.get(CustomerDB, r.customer_id)
        result.append(
            {
                "id": r.id,
                "customer_id": r.customer_id,
                "name": customer.person.display_name,
                "eligible": eligible and r.status == "QUEUED",
                "reason": reason,
                "status": r.status,
                "content": campaign.message_template.replace(
                    "{name}", customer.person.display_name
                ),
            }
        )
    return result


class SendInput(BaseModel):
    reviewed: bool


@router.post("/{campaign_id}/recipients/{recipient_id}/send")
async def send_reviewed(
    campaign_id: str, recipient_id: str, req: SendInput, db: Session = DbSession
):
    if not req.reviewed:
        raise HTTPException(422, "Review the message before sending")
    campaign = require(db, CampaignDB, campaign_id)
    recipient = require(db, CampaignRecipientDB, recipient_id)
    if recipient.campaign_id != campaign.id:
        raise HTTPException(404, "Recipient not found in campaign")
    if recipient.status != "QUEUED":
        raise HTTPException(
            409,
            "Recipient is already processed; ambiguous deliveries are never retried automatically",
        )
    eligible, reason, conv = eligibility(db, campaign, recipient)
    if not eligible:
        raise HTTPException(409, reason)
    customer = db.get(CustomerDB, recipient.customer_id)
    content = campaign.message_template.replace("{name}", customer.person.display_name)
    recipient.status = "SENDING"
    db.commit()
    try:
        delivered = await zalo_oa.send_message(conv.external_conversation_id, content)
    except Exception:
        recipient.status = "UNKNOWN"
        db.commit()
        raise HTTPException(
            502,
            "OA delivery not confirmed; verify in OA before creating another message",
        )
    recipient.status = "SENT" if delivered else "REJECTED"
    if delivered:
        recipient.sent_at = datetime.now(timezone.utc)
        customer.last_interaction = recipient.sent_at
        conv.last_message_at = recipient.sent_at
        db.add(MessageDB(conversation_id=conv.id, sender_type="AGENT", content=content))
        record_event(
            db, customer.person_id, "OA_MESSAGE_SENT", "Gửi tin tư vấn OA đã duyệt"
        )
    campaign.status = "ACTIVE"
    db.commit()
    return {"status": recipient.status}
