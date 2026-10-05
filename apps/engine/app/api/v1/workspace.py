"""Local CRM authoring, pipeline, blacklist, consent and assistance endpoints."""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import DbSession, SessionAuth
from app.domain.models import (
    BlacklistEntityType,
    BlacklistMode,
    NeedProfileData,
    OpportunityStage,
)
from app.infrastructure.database.models import (
    PersonDB,
    PersonPhoneDB,
    NoteDB,
    CustomerDB,
    CustomerNeedProfileDB,
    OpportunityDB,
    TimelineEventDB,
    BlacklistEntityDB,
    PermissionDB,
    SocialPostDB,
    CareTaskDB,
    ScanJobDB,
    ConversationDB,
    MessageDB,
    SocialAccountDB,
    PersonLabelDB,
    LabelDB,
)
from app.modules.identity.phone_normalizer import PhoneNormalizer
from app.modules.crm.care_service import care_service
from app.modules.ai.provider import ai_provider

router = APIRouter(tags=["Workspace"], dependencies=[SessionAuth])


def require(db, model, entity_id):
    row = db.get(model, entity_id)
    if (
        row is None
        or getattr(row, "deleted_at", None)
        or getattr(row, "is_merged", False)
    ):
        raise HTTPException(404, "Record not found")
    return row


def record_event(db, person_id, event_type, title, metadata=None):
    db.add(
        TimelineEventDB(
            person_id=person_id,
            event_type=event_type,
            title=title,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
    )


class PersonInput(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    phone: Optional[str] = None
    source_url: Optional[str] = Field(None, max_length=1024)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()


@router.post("/persons", status_code=201)
def create_person(req: PersonInput, db: Session = DbSession):
    phone = PhoneNormalizer.normalize_single(req.phone) if req.phone else None
    if req.phone and not phone:
        raise HTTPException(422, "Invalid Vietnamese mobile phone")
    person = PersonDB(
        display_name=req.display_name,
        source_type="MANUAL",
        contact_quality_score=85 if phone else 35,
    )
    db.add(person)
    db.flush()
    if phone:
        db.add(
            PersonPhoneDB(
                person_id=person.id,
                raw_phone=req.phone,
                normalized_phone=phone,
                source_type="MANUAL",
                source_url=req.source_url,
                is_verified=False,
            )
        )
    record_event(db, person.id, "PERSON_CREATED", "Tạo hồ sơ liên hệ")
    db.commit()
    return {"id": person.id}


@router.get("/persons/{person_id}")
def person_detail(person_id: str, db: Session = DbSession):
    p = require(db, PersonDB, person_id)
    permission = db.query(PermissionDB).filter_by(person_id=p.id).first()
    return {
        "id": p.id,
        "display_name": p.display_name,
        "source_type": p.source_type,
        "contact_quality_score": p.contact_quality_score,
        "customer_id": p.customer.id if p.customer else None,
        "phones": [
            {
                "id": ph.id,
                "normalized_phone": ph.normalized_phone,
                "raw_phone": ph.raw_phone,
                "source_type": ph.source_type,
                "source_url": ph.source_url,
                "captured_at": ph.captured_at,
                "is_verified": ph.is_verified,
            }
            for ph in p.phones
        ],
        "social_accounts": [
            {
                "platform": s.platform,
                "external_id": s.external_id,
                "profile_url": s.profile_url,
            }
            for s in p.social_accounts
        ],
        "notes": [
            {"id": n.id, "content": n.content, "created_at": n.created_at}
            for n in p.notes
        ],
        "labels": [link.label.name for link in p.person_labels],
        "timeline": [
            {
                "id": t.id,
                "title": t.title,
                "event_type": t.event_type,
                "created_at": t.created_at,
            }
            for t in sorted(p.timeline_events, key=lambda t: t.created_at, reverse=True)
        ],
        "permission": {
            key: bool(getattr(permission, key, False))
            for key in (
                "marketing_allowed",
                "zalo_allowed",
                "opt_out",
                "do_not_contact",
            )
        },
    }


@router.patch("/persons/{person_id}")
def edit_person(person_id: str, req: PersonInput, db: Session = DbSession):
    p = require(db, PersonDB, person_id)
    p.display_name = req.display_name
    if req.phone:
        phone = PhoneNormalizer.normalize_single(req.phone)
        if not phone:
            raise HTTPException(422, "Invalid Vietnamese mobile phone")
        if not any(ph.normalized_phone == phone for ph in p.phones):
            db.add(
                PersonPhoneDB(
                    person_id=p.id,
                    raw_phone=req.phone,
                    normalized_phone=phone,
                    source_type="MANUAL",
                    source_url=req.source_url,
                    is_verified=False,
                )
            )
    record_event(db, p.id, "PERSON_UPDATED", "Cập nhật hồ sơ")
    db.commit()
    return {"status": "UPDATED"}


class NoteInput(BaseModel):
    content: str = Field(min_length=1, max_length=20000)


@router.post("/persons/{person_id}/notes", status_code=201)
def create_note(person_id: str, req: NoteInput, db: Session = DbSession):
    p = require(db, PersonDB, person_id)
    note = NoteDB(person_id=p.id, content=req.content)
    db.add(note)
    record_event(db, p.id, "NOTE_ADDED", "Thêm ghi chú")
    db.commit()
    return {"id": note.id}


class LabelsInput(BaseModel):
    labels: list[str] = Field(max_length=30)


@router.put("/persons/{person_id}/labels")
def set_labels(person_id: str, req: LabelsInput, db: Session = DbSession):
    p = require(db, PersonDB, person_id)
    values = list(dict.fromkeys(v.strip() for v in req.labels if v.strip()))
    if any(len(v) > 64 for v in values):
        raise HTTPException(422, "Label exceeds 64 characters")
    for link in list(p.person_labels):
        db.delete(link)
    db.flush()
    for value in values:
        label = db.query(LabelDB).filter_by(name=value).first()
        if not label:
            label = LabelDB(name=value)
            db.add(label)
            db.flush()
        db.add(PersonLabelDB(person_id=p.id, label_id=label.id))
    db.commit()
    return {"labels": values}


class ConsentInput(BaseModel):
    marketing_allowed: bool = False
    zalo_allowed: bool = False
    opt_out: bool = False
    do_not_contact: bool = False
    source: str = Field(min_length=1, max_length=64)


@router.put("/persons/{person_id}/permission")
def set_permission(person_id: str, req: ConsentInput, db: Session = DbSession):
    p = require(db, PersonDB, person_id)
    row = db.query(PermissionDB).filter_by(person_id=p.id).first()
    if not row:
        row = PermissionDB(person_id=p.id)
        db.add(row)
    for key, value in req.model_dump().items():
        setattr(row, key, value)
    record_event(
        db, p.id, "CONSENT_UPDATED", "Cập nhật quyền liên hệ", req.model_dump()
    )
    db.commit()
    return {"status": "UPDATED"}


@router.get("/customers")
def list_customers(
    status: Optional[OpportunityStage] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = DbSession,
):
    query = db.query(CustomerDB).filter(CustomerDB.deleted_at.is_(None))
    if status:
        query = query.filter(CustomerDB.status == status.value)
    return [
        {
            "id": c.id,
            "person_id": c.person_id,
            "display_name": c.person.display_name,
            "status": c.status,
            "lead_score": c.lead_score,
            "next_care_date": c.next_care_date,
            "phones": [ph.normalized_phone for ph in c.person.phones],
            "need_type": c.need_profile.need_type if c.need_profile else None,
        }
        for c in query.order_by(CustomerDB.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    ]


class StatusInput(BaseModel):
    status: OpportunityStage


@router.patch("/customers/{customer_id}/status")
def customer_status(customer_id: str, req: StatusInput, db: Session = DbSession):
    c = require(db, CustomerDB, customer_id)
    c.status = req.status.value
    record_event(
        db, c.person_id, "STATUS_UPDATED", f"Trạng thái khách hàng: {req.status.value}"
    )
    db.commit()
    return {"status": c.status}


@router.put("/customers/{customer_id}/need-profile")
def update_need(customer_id: str, req: NeedProfileData, db: Session = DbSession):
    c = require(db, CustomerDB, customer_id)
    need = c.need_profile
    if not need:
        need = CustomerNeedProfileDB(customer_id=c.id)
        db.add(need)
    for key, value in req.model_dump(mode="json").items():
        setattr(need, key, value)
    record_event(db, c.person_id, "NEED_UPDATED", "Cập nhật nhu cầu")
    db.commit()
    return req


class OpportunityInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    stage: OpportunityStage = OpportunityStage.NEW
    expected_revenue: float = Field(default=0, ge=0, le=9999999999, allow_inf_nan=False)
    notes: Optional[str] = Field(None, max_length=20000)


class OpportunityPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    stage: Optional[OpportunityStage] = None
    expected_revenue: Optional[float] = Field(
        None, ge=0, le=9999999999, allow_inf_nan=False
    )
    notes: Optional[str] = Field(None, max_length=20000)


@router.post("/customers/{customer_id}/opportunities", status_code=201)
def create_opportunity(
    customer_id: str, req: OpportunityInput, db: Session = DbSession
):
    c = require(db, CustomerDB, customer_id)
    opp = OpportunityDB(customer_id=c.id, **req.model_dump(mode="json"))
    if req.stage in (OpportunityStage.WON, OpportunityStage.LOST):
        opp.closed_at = datetime.now(timezone.utc)
    db.add(opp)
    record_event(db, c.person_id, "OPPORTUNITY_CREATED", req.title)
    db.commit()
    return {"id": opp.id}


@router.patch("/opportunities/{opportunity_id}")
def update_opportunity(
    opportunity_id: str, req: OpportunityPatch, db: Session = DbSession
):
    opp = require(db, OpportunityDB, opportunity_id)
    for key, value in req.model_dump(mode="json", exclude_unset=True).items():
        if value is None and key != "notes":
            raise HTTPException(422, f"{key} cannot be null")
        setattr(opp, key, value)
    if "stage" in req.model_fields_set:
        opp.closed_at = (
            datetime.now(timezone.utc)
            if req.stage in (OpportunityStage.WON, OpportunityStage.LOST)
            else None
        )
    record_event(
        db, opp.customer.person_id, "OPPORTUNITY_UPDATED", f"{opp.title}: {opp.stage}"
    )
    db.commit()
    return {"status": "UPDATED"}


class BlacklistInput(BaseModel):
    entity_type: BlacklistEntityType
    value: str = Field(min_length=1, max_length=255)
    mode: BlacklistMode = BlacklistMode.HARD_BLACKLIST
    reason: str = Field(default="", max_length=255)


@router.get("/blacklist")
def list_blacklist(db: Session = DbSession):
    return [
        {
            "id": r.id,
            "entity_type": r.entity_type,
            "value": r.value,
            "mode": r.mode,
            "reason": r.reason,
        }
        for r in db.query(BlacklistEntityDB)
        .order_by(BlacklistEntityDB.created_at.desc())
        .all()
    ]


@router.post("/blacklist", status_code=201)
def create_blacklist(req: BlacklistInput, db: Session = DbSession):
    value = req.value.strip().lower()
    if req.entity_type == BlacklistEntityType.PHONE:
        value = PhoneNormalizer.normalize_single(value)
    if not value:
        raise HTTPException(422, "Invalid blacklist value")
    row = (
        db.query(BlacklistEntityDB)
        .filter_by(entity_type=req.entity_type.value, value=value)
        .first()
    )
    if not row:
        row = BlacklistEntityDB(entity_type=req.entity_type.value, value=value)
        db.add(row)
    row.mode, row.reason = req.mode.value, req.reason
    db.commit()
    return {"id": row.id}


@router.delete("/blacklist/{rule_id}")
def delete_blacklist(rule_id: str, db: Session = DbSession):
    db.delete(require(db, BlacklistEntityDB, rule_id))
    db.commit()
    return {"status": "DELETED"}


@router.get("/care-tasks/proposals")
def followup_proposals(db: Session = DbSession):
    return care_service.evaluate_followup_rules(db)


@router.get("/dashboard")
def dashboard(db: Session = DbSession):
    now = datetime.now(timezone.utc)
    return {
        "posts": db.query(SocialPostDB)
        .filter(SocialPostDB.deleted_at.is_(None))
        .count(),
        "persons": db.query(PersonDB)
        .filter(PersonDB.deleted_at.is_(None), PersonDB.is_merged.is_(False))
        .count(),
        "customers": db.query(CustomerDB)
        .filter(CustomerDB.deleted_at.is_(None))
        .count(),
        "overdue": db.query(CareTaskDB)
        .filter(
            CareTaskDB.status == "PENDING",
            CareTaskDB.deleted_at.is_(None),
            CareTaskDB.scheduled_at < now,
        )
        .count(),
        "active_scans": db.query(ScanJobDB)
        .filter(ScanJobDB.status.in_(["RUNNING", "PAUSED"]))
        .count(),
    }


@router.get("/export/customers")
def export_customers(db: Session = DbSession):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "phones", "status", "need_type", "lead_score"])

    def safe(value):
        text = str(value or "")
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text

    for c in db.query(CustomerDB).filter(CustomerDB.deleted_at.is_(None)).all():
        writer.writerow(
            [
                c.id,
                safe(c.person.display_name),
                safe(";".join(ph.normalized_phone for ph in c.person.phones)),
                c.status,
                c.need_profile.need_type if c.need_profile else "",
                c.lead_score,
            ]
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="scansocial-customers.csv"'
        },
    )


class ConversationInput(BaseModel):
    person_id: str
    external_conversation_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)


@router.get("/conversations")
def list_conversations(db: Session = DbSession):
    return [
        {
            "id": c.id,
            "title": c.title,
            "person_id": c.linked_person_id,
            "external_conversation_id": c.external_conversation_id,
            "last_message_at": c.last_message_at,
        }
        for c in db.query(ConversationDB)
        .order_by(ConversationDB.last_message_at.desc())
        .all()
    ]


@router.post("/conversations", status_code=201)
def create_conversation(req: ConversationInput, db: Session = DbSession):
    require(db, PersonDB, req.person_id)
    row = (
        db.query(ConversationDB)
        .filter_by(
            platform="ZALO", external_conversation_id=req.external_conversation_id
        )
        .first()
    )
    if not row:
        row = ConversationDB(
            platform="ZALO", external_conversation_id=req.external_conversation_id
        )
        db.add(row)
    row.title, row.linked_person_id = req.title, req.person_id
    db.commit()
    return {"id": row.id}


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, db: Session = DbSession):
    require(db, ConversationDB, conversation_id)
    return [
        {
            "id": m.id,
            "sender_type": m.sender_type,
            "content": m.content,
            "sent_at": m.sent_at,
        }
        for m in db.query(MessageDB)
        .filter_by(conversation_id=conversation_id)
        .order_by(MessageDB.sent_at.asc())
        .all()
    ]


class MessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    sender_type: str = Field(default="CUSTOMER", pattern="^(CUSTOMER|AGENT)$")


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def log_message(conversation_id: str, req: MessageInput, db: Session = DbSession):
    c = require(db, ConversationDB, conversation_id)
    c.last_message_at = datetime.now(timezone.utc)
    row = MessageDB(conversation_id=c.id, **req.model_dump())
    db.add(row)
    if c.linked_person_id:
        person = require(db, PersonDB, c.linked_person_id)
        if person.customer:
            person.customer.last_interaction = c.last_message_at
        record_event(db, person.id, "MESSAGE_LOGGED", "Ghi nhận hội thoại Zalo")
    db.commit()
    return {"id": row.id, "status": "RECORDED"}


@router.post("/conversations/{conversation_id}/suggestion")
async def suggest_reply(conversation_id: str, db: Session = DbSession):
    c = require(db, ConversationDB, conversation_id)
    p = require(db, PersonDB, c.linked_person_id) if c.linked_person_id else None
    last = (
        db.query(MessageDB)
        .filter_by(conversation_id=c.id)
        .order_by(MessageDB.sent_at.desc())
        .first()
    )
    summary = p.display_name if p else ""
    reply = await ai_provider.generate_reply_suggestion(
        summary, last.content if last else ""
    )
    return {"draft": reply, "requires_manual_send": True}
