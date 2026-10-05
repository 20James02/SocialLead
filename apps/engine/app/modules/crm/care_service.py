from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.infrastructure.database.models import (
    CareTaskDB,
    CustomerDB,
    OpportunityDB,
    TimelineEventDB,
)
from app.domain.models import CarePriority, CareTaskStatus, OpportunityStage


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class CareService:
    """
    Care Calendar, Task Management & Follow-up Automation Rules Engine.
    """

    @classmethod
    def create_task(
        cls,
        db: Session,
        customer_id: str,
        title: str,
        scheduled_at: datetime,
        priority: CarePriority = CarePriority.MEDIUM,
        description: Optional[str] = None,
        opportunity_id: Optional[str] = None,
    ) -> CareTaskDB:
        customer = (
            db.query(CustomerDB)
            .filter(CustomerDB.id == customer_id, CustomerDB.deleted_at.is_(None))
            .first()
        )
        if not customer:
            raise ValueError("Customer not found")
        if opportunity_id:
            opportunity = (
                db.query(OpportunityDB)
                .filter(
                    OpportunityDB.id == opportunity_id,
                    OpportunityDB.customer_id == customer_id,
                    OpportunityDB.deleted_at.is_(None),
                )
                .first()
            )
            if not opportunity:
                raise ValueError("Opportunity does not belong to this customer")
        task = CareTaskDB(
            customer_id=customer_id,
            opportunity_id=opportunity_id,
            title=title,
            description=description,
            scheduled_at=to_utc(scheduled_at),
            priority=priority.value,
            status=CareTaskStatus.PENDING.value,
        )
        db.add(task)

        # Update customer next_care_date with timezone-safe comparison
        customer = db.query(CustomerDB).filter(CustomerDB.id == customer_id).first()
        if customer:
            sched_utc = to_utc(scheduled_at)
            curr_next_utc = to_utc(customer.next_care_date)
            if not curr_next_utc or sched_utc < curr_next_utc:
                customer.next_care_date = scheduled_at

        db.commit()
        db.refresh(task)
        return task

    @classmethod
    def complete_task(
        cls, db: Session, task_id: str, notes: Optional[str] = None
    ) -> CareTaskDB:
        task = db.query(CareTaskDB).filter(CareTaskDB.id == task_id).first()
        if not task:
            raise ValueError(f"Care task {task_id} not found")
        if task.status == CareTaskStatus.COMPLETED.value:
            return task
        if task.status != CareTaskStatus.PENDING.value or task.deleted_at:
            raise ValueError("Only pending tasks can be completed")

        task.status = CareTaskStatus.COMPLETED.value
        task.completed_at = datetime.now(timezone.utc)
        if notes and task.description:
            task.description += f"\n[Completed Note]: {notes}"
        elif notes:
            task.description = f"[Completed Note]: {notes}"

        # Update customer last interaction
        customer = (
            db.query(CustomerDB).filter(CustomerDB.id == task.customer_id).first()
        )
        if customer:
            customer.last_interaction = datetime.now(timezone.utc)
            db.flush()
            next_task = (
                db.query(CareTaskDB)
                .filter(
                    CareTaskDB.customer_id == customer.id,
                    CareTaskDB.status == "PENDING",
                    CareTaskDB.deleted_at.is_(None),
                )
                .order_by(CareTaskDB.scheduled_at)
                .first()
            )
            customer.next_care_date = next_task.scheduled_at if next_task else None
            db.add(
                TimelineEventDB(
                    person_id=customer.person_id,
                    event_type="CARE_COMPLETED",
                    title=task.title,
                )
            )

        db.commit()
        db.refresh(task)
        return task

    @classmethod
    def is_task_overdue(cls, task: CareTaskDB) -> bool:
        if task.status != CareTaskStatus.PENDING.value:
            return False
        now_utc = datetime.now(timezone.utc)
        sched_utc = to_utc(task.scheduled_at)
        return sched_utc < now_utc

    @classmethod
    def evaluate_followup_rules(cls, db: Session) -> List[dict]:
        """
        Rule: If Opportunity is in stage QUOTED and has had no update for > 48 hours,
        propose an automated follow-up care task.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        proposals = []

        stale_opps = (
            db.query(OpportunityDB)
            .filter(
                OpportunityDB.stage == OpportunityStage.QUOTED.value,
                OpportunityDB.deleted_at.is_(None),
                OpportunityDB.updated_at < cutoff,
            )
            .all()
        )

        for opp in stale_opps:
            existing_task = (
                db.query(CareTaskDB)
                .filter(
                    CareTaskDB.opportunity_id == opp.id,
                    CareTaskDB.status == CareTaskStatus.PENDING.value,
                    CareTaskDB.deleted_at.is_(None),
                )
                .first()
            )

            if not existing_task:
                proposals.append(
                    {
                        "rule": "QUOTED_NO_RESPONSE_48H",
                        "customer_id": opp.customer_id,
                        "opportunity_id": opp.id,
                        "recommended_title": f"Follow-up báo giá: {opp.title}",
                        "suggested_time": datetime.now(timezone.utc)
                        + timedelta(hours=2),
                    }
                )

        return proposals


care_service = CareService()
