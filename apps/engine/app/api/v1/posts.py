from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
from app.infrastructure.database.models import (
    PersonDB,
    PersonPhoneDB,
    SocialAccountDB,
    TimelineEventDB,
    AIAnalysisDB,
)
from app.modules.identity.phone_normalizer import PhoneNormalizer

from app.api.deps import DbSession, SessionAuth
from app.infrastructure.database.models import (
    SocialPostDB,
    SocialCommentDB,
    SavedPostDB,
)
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
    db: Session = DbSession,
):
    query = db.query(SocialPostDB).filter(SocialPostDB.deleted_at == None)

    if lead_score_min is not None:
        query = query.filter(SocialPostDB.lead_score >= lead_score_min)
    if has_phone is True:
        query = query.filter(SocialPostDB.phone_extracted != None)
    elif has_phone is False:
        query = query.filter(SocialPostDB.phone_extracted == None)
    if is_saved is True:
        query = query.filter(SocialPostDB.saved_entry.has())
    elif is_saved is False:
        query = query.filter(~SocialPostDB.saved_entry.has())

    posts = (
        query.order_by(SocialPostDB.posted_at.desc()).offset(offset).limit(limit).all()
    )
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
                is_saved=is_p_saved,
            )
        )
    return results


@router.get("/{post_id}", response_model=PostDetailResponse)
def get_post_detail(post_id: str, db: Session = DbSession):
    p = (
        db.query(SocialPostDB)
        .filter(SocialPostDB.id == post_id, SocialPostDB.deleted_at.is_(None))
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")

    is_saved = (
        db.query(SavedPostDB).filter(SavedPostDB.post_id == p.id).first() is not None
    )
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
        is_saved=is_saved,
    )


@router.post("/{post_id}/save")
def save_post(post_id: str, note: Optional[str] = None, db: Session = DbSession):
    p = db.query(SocialPostDB).filter(SocialPostDB.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = db.query(SavedPostDB).filter(SavedPostDB.post_id == post_id).first()
    if not existing:
        saved = SavedPostDB(post_id=post_id, user_note=note)
        p.is_raw = False  # Protect permanently from cleanup
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


@router.get("/{post_id}/analysis")
def post_analysis(post_id: str, db: Session = DbSession):
    row = db.query(AIAnalysisDB).filter_by(post_id=post_id).first()
    if not row:
        raise HTTPException(404, "Post analysis not found")
    return json.loads(row.explanation_json)


@router.get("/{post_id}/comments")
def post_comments(post_id: str, db: Session = DbSession):
    post = db.get(SocialPostDB, post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    return [
        {
            "id": c.id,
            "author_name": c.author_name,
            "content": c.content,
            "intent_score": c.intent_score,
            "detected_phone": c.detected_phone,
            "posted_at": c.posted_at,
        }
        for c in post.comments
    ]


def promote_author(
    db, name, author_url, author_id, platform, content, source_url, source_type
):
    account = (
        db.query(SocialAccountDB)
        .filter_by(platform=platform, external_id=author_id)
        .first()
        if author_id
        else None
    )
    person = account.person if account else None
    if person and person.is_merged:
        person = db.get(PersonDB, person.merged_into_id)
    if not person:
        person = PersonDB(
            display_name=name, source_type=platform, contact_quality_score=35
        )
        db.add(person)
        db.flush()
        if author_id:
            db.add(
                SocialAccountDB(
                    person_id=person.id,
                    platform=platform,
                    external_id=author_id,
                    profile_url=author_url,
                )
            )
    phones = PhoneNormalizer.extract_and_normalize_all(
        content, source_type=source_type, source_url=source_url
    )
    existing = {p.normalized_phone for p in person.phones}
    for phone in phones:
        if phone.normalized_phone not in existing:
            db.add(PersonPhoneDB(person_id=person.id, **phone.model_dump()))
            existing.add(phone.normalized_phone)
    person.contact_quality_score = 85 if phones or existing else 35
    db.add(
        TimelineEventDB(
            person_id=person.id,
            event_type="POST_LINKED",
            title="Lưu nguồn khách hàng",
            metadata_json=json.dumps({"source_url": source_url}, ensure_ascii=False),
        )
    )
    return person


@router.post("/{post_id}/promote")
def promote_post(post_id: str, db: Session = DbSession):
    post = db.get(SocialPostDB, post_id)
    if not post or post.deleted_at:
        raise HTTPException(404, "Post not found")
    saved = post.saved_entry
    if saved and saved.person_id:
        person = db.get(PersonDB, saved.person_id)
        return {"person_id": person.merged_into_id if person.is_merged else person.id}
    person = promote_author(
        db,
        post.author_name,
        post.author_url,
        post.author_id,
        post.platform,
        post.content,
        post.url,
        "SOCIAL_POST",
    )
    post.is_raw = False
    if saved:
        saved.person_id = person.id
    else:
        db.add(SavedPostDB(post_id=post.id, person_id=person.id))
    db.commit()
    return {"person_id": person.id}


@router.post("/{post_id}/comments/{comment_id}/promote")
def promote_comment(post_id: str, comment_id: str, db: Session = DbSession):
    comment = (
        db.query(SocialCommentDB).filter_by(id=comment_id, post_id=post_id).first()
    )
    if not comment:
        raise HTTPException(404, "Comment not found")
    author_key = comment.author_url or f"comment:{comment.id}"
    person = promote_author(
        db,
        comment.author_name,
        comment.author_url,
        author_key,
        comment.post.platform,
        comment.content,
        comment.post.url,
        "SOCIAL_COMMENT",
    )
    comment.post.is_raw = False
    db.commit()
    return {"person_id": person.id}
