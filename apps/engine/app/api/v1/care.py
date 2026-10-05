from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import DbSession, SessionAuth
from app.infrastructure.database.models import CareTaskDB
from app.domain.models import CarePriority, CareTaskStatus
from app.modules.crm.care_service import care_service

router = APIRouter(prefix="/care-tasks", tags=["Care Calendar"], dependencies=[SessionAuth])

class CreateCareTaskRequest(BaseModel):
    customer_id: str
    title: str
    scheduled_at: datetime
    priority: CarePriority = CarePriority.MEDIUM
    description: Optional[str] = None
    opportunity_id: Optional[str] = None

class CareTaskItem(BaseModel):
    id: str
    customer_id: str
    opportunity_id: Optional[str]
    title: str
    description: Optional[str]
    scheduled_at: datetime
    priority: str
    status: str
    is_overdue: bool
    completed_at: Optional[datetime]

@router.get("", response_model=List[CareTaskItem])
def list_care_tasks(
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = DbSession
):
    query = db.query(CareTaskDB).filter(CareTaskDB.deleted_at == None)
    if status_filter:
        query = query.filter(CareTaskDB.status == status_filter.upper())
    
    tasks = query.order_by(CareTaskDB.scheduled_at.asc()).limit(limit).all()
    results = []
    for t in tasks:
        results.append(
            CareTaskItem(
                id=t.id,
                customer_id=t.customer_id,
                opportunity_id=t.opportunity_id,
                title=t.title,
                description=t.description,
                scheduled_at=t.scheduled_at,
                priority=t.priority,
                status=t.status,
                is_overdue=care_service.is_task_overdue(t),
                completed_at=t.completed_at
            )
        )
    return results

@router.post("", response_model=CareTaskItem, status_code=status.HTTP_201_CREATED)
def create_care_task(req: CreateCareTaskRequest, db: Session = DbSession):
    task = care_service.create_task(
        db=db,
        customer_id=req.customer_id,
        title=req.title,
        scheduled_at=req.scheduled_at,
        priority=req.priority,
        description=req.description,
        opportunity_id=req.opportunity_id
    )
    return CareTaskItem(
        id=task.id,
        customer_id=task.customer_id,
        opportunity_id=task.opportunity_id,
        title=task.title,
        description=task.description,
        scheduled_at=task.scheduled_at,
        priority=task.priority,
        status=task.status,
        is_overdue=care_service.is_task_overdue(task),
        completed_at=task.completed_at
    )

@router.patch("/{task_id}/complete")
def complete_care_task(task_id: str, note: Optional[str] = None, db: Session = DbSession):
    try:
        task = care_service.complete_task(db=db, task_id=task_id, notes=note)
        return {"status": "SUCCESS", "task_id": task.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
