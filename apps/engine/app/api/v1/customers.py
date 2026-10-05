from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import DbSession, SessionAuth
from app.infrastructure.database.models import (
    CustomerDB, CustomerNeedProfileDB, OpportunityDB, TimelineEventDB, NoteDB
)

router = APIRouter(prefix="/customers", tags=["Customers 360"], dependencies=[SessionAuth])

class OpportunityItem(BaseModel):
    id: str
    title: str
    stage: str
    expected_revenue: float
    created_at: datetime

class TimelineItem(BaseModel):
    id: str
    event_type: str
    title: str
    metadata_json: Optional[str]
    created_at: datetime

class Customer360Response(BaseModel):
    id: str
    person_id: str
    display_name: str
    status: str
    lead_score: int
    assigned_to: Optional[str]
    next_care_date: Optional[datetime]
    last_interaction: Optional[datetime]
    need_type: Optional[str]
    property_type: Optional[str]
    province: Optional[str]
    urgency: Optional[str]
    opportunities: List[OpportunityItem]
    timeline: List[TimelineItem]

@router.get("/{customer_id}", response_model=Customer360Response)
def get_customer_360(customer_id: str, db: Session = DbSession):
    cust = db.query(CustomerDB).filter(CustomerDB.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    need = cust.need_profile
    opps = [
        OpportunityItem(
            id=o.id,
            title=o.title,
            stage=o.stage,
            expected_revenue=float(o.expected_revenue or 0.0),
            created_at=o.created_at
        )
        for o in cust.opportunities
    ]

    events = [
        TimelineItem(
            id=t.id,
            event_type=t.event_type,
            title=t.title,
            metadata_json=t.metadata_json,
            created_at=t.created_at
        )
        for t in cust.person.timeline_events
    ]

    return Customer360Response(
        id=cust.id,
        person_id=cust.person_id,
        display_name=cust.person.display_name,
        status=cust.status,
        lead_score=cust.lead_score,
        assigned_to=cust.assigned_to,
        next_care_date=cust.next_care_date,
        last_interaction=cust.last_interaction,
        need_type=need.need_type if need else None,
        property_type=need.property_type if need else None,
        province=need.province if need else None,
        urgency=need.urgency if need else None,
        opportunities=opps,
        timeline=events
    )
