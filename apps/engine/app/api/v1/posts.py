from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import DbSession, SessionAuth
from app.infrastructure.database.models import SocialPostDB, SocialCommentDB, SavedPostDB
from app.modules.scanner.blacklist import blacklist_engine

router = APIRouter(prefix="/posts", tags=["Posts"], dependencies=[SessionAuth])

class PostListItem(BaseModel):
    id: str
    platform: str
    url: str
    author_name: str
    content: str
    group_name: Optional[str]
    lead_score: int
    intent_score: int
    spam_score: int
    urgency: str
    phone_extracted: Optional[str]
    posted_at: datetime
    is_saved: bool = False

class PostDetailResponse(PostListItem):
    external_id: str
    author_id: Optional[str]
    author_url: Optional[str]
    group_url: Optional[str]
    detected_at: datetime
    is_raw: bool

@router.get("", response_model=List[PostListItem])
def list_posts(
    lead_score_min: Optional[int] = Query(None, ge=0, le=100),
    has_phone: Optional[bool] = Query(None),
    is_saved: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = DbSession
):
    query = db.query(SocialPostDB).filter(SocialPostDB.deleted_at == None)
    
    if lead_score_min is not None:
        query = query.filter(SocialPostDB.lead_score >= lead_score_min)
    if has_phone is True:
        query = query.filter(SocialPostDB.phone_extracted != None)
    elif has_phone is False:
        query = query.filter(SocialPostDB.phone_extracted == None)

    posts = query.order_by(SocialPostDB.posted_at.desc()).offset(offset).limit(limit).all()
    saved_ids = {r[0] for r in db.query(SavedPostDB.post_id).all()}

    results = []
    for p in posts:
        is_p_saved = p.id in saved_ids
        if is_saved is not None and is_p_saved != is_saved:
            continue
        results.append(
            PostListItem(
                id=p.id,
                platform=p.platform,
                url=p.url,
                author_name=p.author_name,
                content=p.content[:300],
                group_name=p.group_name,
                lead_score=p.lead_score,
                intent_score=p.intent_score,
                spam_score=p.spam_score,
                urgency=p.urgency,
                phone_extracted=p.phone_extracted,
                posted_at=p.posted_at,
                is_saved=is_p_saved
            )
        )
    return results

@router.get("/{post_id}", response_model=PostDetailResponse)
def get_post_detail(post_id: str, db: Session = DbSession):
    p = db.query(SocialPostDB).filter(SocialPostDB.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    
    is_saved = db.query(SavedPostDB).filter(SavedPostDB.post_id == p.id).first() is not None
    return PostDetailResponse(
        id=p.id,
        platform=p.platform,
        external_id=p.external_id,
        url=p.url,
        author_id=p.author_id,
        author_name=p.author_name,
        author_url=p.author_url,
        content=p.content,
        group_name=p.group_name,
        group_url=p.group_url,
        lead_score=p.lead_score,
        intent_score=p.intent_score,
        spam_score=p.spam_score,
        urgency=p.urgency,
        phone_extracted=p.phone_extracted,
        posted_at=p.posted_at,
        detected_at=p.detected_at,
        is_raw=p.is_raw,
        is_saved=is_saved
    )

@router.post("/{post_id}/save")
def save_post(post_id: str, note: Optional[str] = None, db: Session = DbSession):
    p = db.query(SocialPostDB).filter(SocialPostDB.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    
    existing = db.query(SavedPostDB).filter(SavedPostDB.post_id == post_id).first()
    if not existing:
        saved = SavedPostDB(post_id=post_id, user_note=note)
        p.is_raw = False # Protect permanently from cleanup
        db.add(saved)
        db.commit()
    return {"status": "SAVED", "post_id": post_id}

@router.delete("/{post_id}/save")
def unsave_post(post_id: str, db: Session = DbSession):
    saved = db.query(SavedPostDB).filter(SavedPostDB.post_id == post_id).first()
    if saved:
        db.delete(saved)
        db.commit()
    return {"status": "UNSAVED", "post_id": post_id}
