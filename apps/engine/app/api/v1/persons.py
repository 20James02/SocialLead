from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from pydantic import Field
import json
from app.domain.models import NeedType, PropertyType, LeadUrgency

from app.api.deps import DbSession, SessionAuth
from app.infrastructure.database.models import (
    PersonDB,
    PersonPhoneDB,
    SocialAccountDB,
    CustomerDB,
    CustomerNeedProfileDB,
    OpportunityDB,
    TimelineEventDB,
)
from app.modules.identity.identity_resolver import identity_resolver

router = APIRouter(
    prefix="/persons", tags=["Persons / CRM"], dependencies=[SessionAuth]
)


class PersonPhoneResponse(BaseModel):
    id: str
    normalized_phone: str
    raw_phone: str
    source_type: str
    is_verified: bool


class PersonListItem(BaseModel):
    id: str
    display_name: str
    avatar_url: Optional[str]
    contact_quality_score: int
    source_type: str
    phones: List[str]
    is_customer: bool
    first_seen: datetime


class ConvertCustomerRequest(BaseModel):
    need_type: NeedType
    property_type: PropertyType = PropertyType.UNKNOWN
    province: Optional[str] = None
    urgency: LeadUrgency = LeadUrgency.MEDIUM
    initial_opportunity_title: Optional[str] = None
    expected_revenue: float = Field(
        default=0.0, ge=0, le=9999999999, allow_inf_nan=False
    )


class MergePersonsRequest(BaseModel):
    primary_person_id: str
    duplicate_person_id: str
    merge_reason: str = "User confirmed duplicate merge"


@router.get("", response_model=List[PersonListItem])
def list_persons(
    has_phone: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = DbSession,
):
    query = db.query(PersonDB).filter(
        PersonDB.deleted_at == None, PersonDB.is_merged == False
    )
    if has_phone is True:
        query = query.filter(PersonDB.phones.any())
    elif has_phone is False:
        query = query.filter(~PersonDB.phones.any())
    persons = (
        query.order_by(PersonDB.last_seen.desc()).offset(offset).limit(limit).all()
    )

    results = []
    for p in persons:
        phone_list = [ph.normalized_phone for ph in p.phones]
        if has_phone is True and not phone_list:
            continue
        elif has_phone is False and phone_list:
            continue

        results.append(
            PersonListItem(
                id=p.id,
                display_name=p.display_name,
                avatar_url=p.avatar_url,
                contact_quality_score=p.contact_quality_score,
                source_type=p.source_type,
                phones=phone_list,
                is_customer=p.customer is not None,
                first_seen=p.first_seen,
            )
        )
    return results


@router.post("/{person_id}/convert-customer")
def convert_person_to_customer(
    person_id: str, req: ConvertCustomerRequest, db: Session = DbSession
):
    person = (
        db.query(PersonDB)
        .filter(
            PersonDB.id == person_id,
            PersonDB.deleted_at.is_(None),
            PersonDB.is_merged.is_(False),
        )
        .first()
    )
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    if person.customer:
        raise HTTPException(status_code=400, detail="Person is already a Customer")

    customer = CustomerDB(
        person_id=person.id, status="NEW", lead_score=person.contact_quality_score
    )
    db.add(customer)
    db.flush()

    need = CustomerNeedProfileDB(
        customer_id=customer.id,
        need_type=req.need_type,
        property_type=req.property_type,
        province=req.province,
        urgency=req.urgency,
    )
    db.add(need)

    if req.initial_opportunity_title:
        opp = OpportunityDB(
            customer_id=customer.id,
            title=req.initial_opportunity_title,
            stage="NEW",
            expected_revenue=req.expected_revenue,
        )
        db.add(opp)

    timeline = TimelineEventDB(
        person_id=person.id,
        event_type="CUSTOMER_CREATED",
        title="Chuyển đổi thành Khách hàng trong CRM",
        metadata_json=json.dumps({"need_type": req.need_type.value}),
    )
    db.add(timeline)

    db.commit()
    db.refresh(customer)
    return {"status": "SUCCESS", "customer_id": customer.id}


@router.post("/merge")
def merge_persons(req: MergePersonsRequest, db: Session = DbSession):
    try:
        merged = identity_resolver.merge_persons(
            db=db,
            primary_id=req.primary_person_id,
            duplicate_id=req.duplicate_person_id,
            reason=req.merge_reason,
        )
        return {"status": "SUCCESS", "primary_id": merged.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
