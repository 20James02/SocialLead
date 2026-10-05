import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import DbSession, SessionAuth
from app.infrastructure.database.models import ScanJobDB, SocialPostDB, ScanResultDB
from app.domain.models import ScanJobStatus, PlatformType, BlacklistMode
from app.core.events import event_bus

router = APIRouter(prefix="/scans", tags=["Scans"], dependencies=[SessionAuth])

class CreateScanRequest(BaseModel):
    platform: PlatformType = PlatformType.FACEBOOK
    keywords: List[str] = Field(min_length=1)
    max_posts: int = Field(default=500, ge=1, le=5000)
    max_age_hours: int = Field(default=24, ge=1, le=168)
    blacklist_mode: BlacklistMode = BlacklistMode.HARD_BLACKLIST

class ScanJobResponse(BaseModel):
    id: str
    platform: str
    status: str
    keywords: List[str]
    max_posts: int
    scanned_count: int
    matched_count: int
    qualified_count: int
    spam_count: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

@router.post("", response_model=ScanJobResponse, status_code=status.HTTP_201_CREATED)
async def create_scan_job(req: CreateScanRequest, db: Session = DbSession):
    job = ScanJobDB(
        platform=req.platform.value,
        keywords_json=json.dumps(req.keywords, ensure_ascii=False),
        max_posts=req.max_posts,
        max_age_hours=req.max_age_hours,
        blacklist_mode=req.blacklist_mode.value,
        status=ScanJobStatus.RUNNING.value,
        started_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Broadcast event
    await event_bus.publish(
        event_type="SCAN_STARTED",
        source_module="api.scans",
        payload={"job_id": job.id, "platform": job.platform}
    )

    return ScanJobResponse(
        id=job.id,
        platform=job.platform,
        status=job.status,
        keywords=json.loads(job.keywords_json),
        max_posts=job.max_posts,
        scanned_count=job.scanned_count,
        matched_count=job.matched_count,
        qualified_count=job.qualified_count,
        spam_count=job.spam_count,
        started_at=job.started_at,
        finished_at=job.finished_at
    )

@router.get("/{job_id}", response_model=ScanJobResponse)
def get_scan_job(job_id: str, db: Session = DbSession):
    job = db.query(ScanJobDB).filter(ScanJobDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return ScanJobResponse(
        id=job.id,
        platform=job.platform,
        status=job.status,
        keywords=json.loads(job.keywords_json),
        max_posts=job.max_posts,
        scanned_count=job.scanned_count,
        matched_count=job.matched_count,
        qualified_count=job.qualified_count,
        spam_count=job.spam_count,
        started_at=job.started_at,
        finished_at=job.finished_at
    )

@router.post("/{job_id}/pause")
def pause_scan_job(job_id: str, db: Session = DbSession):
    job = db.query(ScanJobDB).filter(ScanJobDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    job.status = ScanJobStatus.PAUSED.value
    db.commit()
    return {"status": "PAUSED"}

@router.post("/{job_id}/resume")
def resume_scan_job(job_id: str, db: Session = DbSession):
    job = db.query(ScanJobDB).filter(ScanJobDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    job.status = ScanJobStatus.RUNNING.value
    db.commit()
    return {"status": "RUNNING"}

@router.post("/{job_id}/stop")
def stop_scan_job(job_id: str, db: Session = DbSession):
    job = db.query(ScanJobDB).filter(ScanJobDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    job.status = ScanJobStatus.STOPPED.value
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "STOPPED"}
