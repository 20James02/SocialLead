import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.api.deps import DbSession, SessionAuth
from app.infrastructure.database.models import ScanJobDB
from app.infrastructure.database.session import SessionLocal
from app.domain.models import PlatformType, BlacklistMode
from app.integrations.base import NormalizedSocialPost, NormalizedSocialComment
from app.integrations.official import discover
from app.modules.scanner.pipeline import ingest
from app.core.events import event_bus
from app.core.runtime import operation_lock

router = APIRouter(prefix="/scans", tags=["Scans"], dependencies=[SessionAuth])
workers: dict[str, asyncio.Task] = {}


class CreateScanRequest(BaseModel):
    platform: PlatformType = PlatformType.FACEBOOK
    keywords: list[str] = Field(min_length=1, max_length=30)
    max_posts: int = Field(default=500, ge=1, le=5000)
    max_age_hours: int = Field(default=24, ge=1, le=168)
    blacklist_mode: BlacklistMode = BlacklistMode.HARD_BLACKLIST

    @field_validator("keywords")
    @classmethod
    def valid_keywords(cls, values):
        if any(not k.strip() or len(k) > 200 for k in values):
            raise ValueError("Keywords must contain 1 to 200 characters")
        return list(dict.fromkeys(k.strip() for k in values))


class ImportedPost(NormalizedSocialPost):
    external_id: str = Field(min_length=1, max_length=128)
    author_name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=100000)
    url: str = Field(min_length=1, max_length=1024, pattern=r"^https?://")
    platform: PlatformType
    comments: list[NormalizedSocialComment] = Field(
        default_factory=list, max_length=500
    )


class ImportRequest(BaseModel):
    platform: PlatformType = PlatformType.FACEBOOK
    posts: list[ImportedPost] = Field(min_length=1, max_length=5000)
    keywords: list[str] = Field(default_factory=list, max_length=30)
    max_age_hours: int = Field(default=168, ge=1, le=87600)

    @field_validator("keywords")
    @classmethod
    def valid_keywords(cls, values):
        return CreateScanRequest.valid_keywords(values)


def serialize(job):
    return {
        key: getattr(job, key)
        for key in (
            "id",
            "platform",
            "status",
            "max_posts",
            "max_age_hours",
            "scanned_count",
            "matched_count",
            "qualified_count",
            "spam_count",
            "error_count",
            "error_message",
            "started_at",
            "finished_at",
        )
    } | {"keywords": json.loads(job.keywords_json)}


async def run_scan(job_id):
    try:
        with SessionLocal() as db:
            job = db.get(ScanJobDB, job_id)
            platform, keywords, maximum = (
                job.platform,
                json.loads(job.keywords_json),
                job.max_posts,
            )
        posts = await discover(platform, keywords, maximum)
        for start in range(0, len(posts), 25):
            while True:
                with SessionLocal() as db:
                    current = db.get(ScanJobDB, job_id).status
                if current == "STOPPED":
                    return
                if current != "PAUSED":
                    break
                await asyncio.sleep(0.2)
            async with operation_lock:
                with SessionLocal() as db:
                    job = db.get(ScanJobDB, job_id)
                    if job.status == "STOPPED":
                        return
                    accepted = ingest(db, job, posts[start : start + 25])
                    db.commit()
                    progress = serialize(job)
            await event_bus.publish("SCAN_PROGRESS", "scanner", progress)
            for post_id in accepted:
                await event_bus.publish(
                    "POST_DISCOVERED", "scanner", {"post_id": post_id, "job_id": job_id}
                )
            await asyncio.sleep(0)
        async with operation_lock:
            with SessionLocal() as db:
                job = db.get(ScanJobDB, job_id)
                if job.status == "STOPPED":
                    return
                job.status, job.finished_at = "COMPLETED", datetime.now(timezone.utc)
                db.commit()
                payload = serialize(job)
        await event_bus.publish("SCAN_COMPLETED", "scanner", payload)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        async with operation_lock:
            with SessionLocal() as db:
                job = db.get(ScanJobDB, job_id)
                if job and job.status != "STOPPED":
                    job.status, job.error_message = "FAILED", str(exc)[:1000]
                    job.error_count += 1
                    job.finished_at = datetime.now(timezone.utc)
                    db.commit()
        await event_bus.publish("SCAN_FAILED", "scanner", {"job_id": job_id})
    finally:
        workers.pop(job_id, None)


@router.get("")
def list_jobs(limit: int = Query(50, ge=1, le=200), db: Session = DbSession):
    return [
        serialize(j)
        for j in db.query(ScanJobDB)
        .order_by(ScanJobDB.created_at.desc())
        .limit(limit)
        .all()
    ]


@router.post("/import", status_code=201)
async def import_posts(req: ImportRequest, db: Session = DbSession):
    if any(p.platform != req.platform for p in req.posts):
        raise HTTPException(422, "All imported posts must match the selected platform")
    job = ScanJobDB(
        platform=req.platform.value,
        keywords_json=json.dumps(req.keywords, ensure_ascii=False),
        max_posts=len(req.posts),
        max_age_hours=req.max_age_hours,
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    comments = {p.external_id: p.comments for p in req.posts}
    posts = [
        NormalizedSocialPost(**p.model_dump(exclude={"comments"})) for p in req.posts
    ]
    ingest(db, job, posts, comments=comments)
    job.status, job.finished_at = "COMPLETED", datetime.now(timezone.utc)
    db.commit()
    result = serialize(job)
    await event_bus.publish("SCAN_COMPLETED", "scanner.import", result)
    return result


@router.post("", status_code=201)
async def create_scan_job(req: CreateScanRequest, db: Session = DbSession):
    if req.platform not in (PlatformType.FACEBOOK, PlatformType.THREADS):
        raise HTTPException(422, "Live discovery supports Facebook and Threads")
    job = ScanJobDB(
        platform=req.platform.value,
        keywords_json=json.dumps(req.keywords, ensure_ascii=False),
        max_posts=req.max_posts,
        max_age_hours=req.max_age_hours,
        blacklist_mode=req.blacklist_mode.value,
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    workers[job.id] = asyncio.create_task(run_scan(job.id))
    await event_bus.publish("SCAN_STARTED", "scanner", {"job_id": job.id})
    return serialize(job)


@router.get("/{job_id}")
def get_scan_job(job_id: str, db: Session = DbSession):
    job = db.get(ScanJobDB, job_id)
    if not job:
        raise HTTPException(404, "Scan job not found")
    return serialize(job)


def transition(job_id, target, allowed, db):
    job = db.get(ScanJobDB, job_id)
    if not job:
        raise HTTPException(404, "Scan job not found")
    if job.status not in allowed:
        raise HTTPException(409, f"Cannot move {job.status} to {target}")
    job.status = target
    if target == "STOPPED":
        job.finished_at = datetime.now(timezone.utc)
        task = workers.get(job_id)
        if task:
            task.cancel()
    db.commit()
    return {"status": target}


@router.post("/{job_id}/pause")
async def pause_scan_job(job_id: str, db: Session = DbSession):
    return transition(job_id, "PAUSED", {"RUNNING"}, db)


@router.post("/{job_id}/resume")
async def resume_scan_job(job_id: str, db: Session = DbSession):
    return transition(job_id, "RUNNING", {"PAUSED"}, db)


@router.post("/{job_id}/stop")
async def stop_scan_job(job_id: str, db: Session = DbSession):
    return transition(job_id, "STOPPED", {"RUNNING", "PAUSED"}, db)
