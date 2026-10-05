import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.domain.models import BlacklistEntityType, BlacklistMode
from app.infrastructure.database.models import (
    SocialPostDB,
    SocialCommentDB,
    ScanResultDB,
    BlacklistEntityDB,
    AIAnalysisDB,
)
from app.modules.scanner.blacklist import BlacklistEvaluator
from app.modules.scanner.deduplicator import PostDeduplicator
from app.modules.identity.phone_normalizer import PhoneNormalizer
from app.modules.scoring.lead_scorer import lead_scorer
from app.modules.crm.care_service import to_utc


def ingest(db: Session, job, posts, *, comments=None):
    rules = BlacklistEvaluator()
    for rule in db.query(BlacklistEntityDB).all():
        rules.add_rule(
            BlacklistEntityType(rule.entity_type),
            rule.value,
            BlacklistMode(rule.mode),
            rule.reason or "",
        )
    keywords = json.loads(job.keywords_json)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=job.max_age_hours)
    dedup = PostDeduplicator()
    accepted = []
    for raw in posts[: job.max_posts]:
        job.scanned_count += 1
        if raw.platform != job.platform:
            job.error_count += 1
            continue
        posted_at = to_utc(raw.posted_at)
        if posted_at < cutoff or posted_at > datetime.now(timezone.utc) + timedelta(
            minutes=5
        ):
            continue
        if keywords and not any(
            keyword.casefold() in raw.content.casefold() for keyword in keywords
        ):
            continue
        stamp = posted_at.isoformat()
        author_key = raw.author_id or raw.author_url or raw.author_name
        canonical = dedup.compute_canonical_hash(
            raw.platform, author_key, raw.content, stamp
        )
        if (
            db.query(SocialPostDB.id)
            .filter(
                SocialPostDB.platform == raw.platform,
                or_(
                    SocialPostDB.external_id == raw.external_id,
                    SocialPostDB.canonical_hash == canonical,
                ),
            )
            .first()
        ):
            continue
        phones = PhoneNormalizer.extract_and_normalize_all(
            raw.content, source_url=raw.url
        )
        hits = [
            rules.evaluate(
                author_id=raw.author_id,
                group_name=raw.group_name,
                phone=ph.normalized_phone if ph else None,
                content=raw.content,
                url=raw.url,
                author_url=raw.author_url,
                group_url=raw.group_url,
            )
            for ph in (phones or [None])
        ]
        if any(hit[1] == BlacklistMode.HARD_BLACKLIST for hit in hits):
            job.spam_count += 1
            continue
        soft = any(hit[1] == BlacklistMode.SOFT_BLACKLIST for hit in hits)
        phone = phones[0].normalized_phone if phones else None
        score = lead_scorer.score_post(raw.content, phone, raw.author_name, soft)
        need = lead_scorer.extract_need_profile(raw.content)
        post = SocialPostDB(
            **raw.model_dump(),
            canonical_hash=canonical,
            lead_score=score.overall_lead_score,
            intent_score=score.intent_score,
            spam_score=score.spam_score,
            urgency=need.urgency.value,
            phone_extracted=phone,
        )
        db.add(post)
        db.flush()
        db.add(ScanResultDB(job_id=job.id, post_id=post.id))
        explanation = {
            "score": score.model_dump(mode="json"),
            "need": need.model_dump(mode="json"),
            "phones": [p.model_dump(mode="json") for p in phones],
        }
        db.add(
            AIAnalysisDB(
                post_id=post.id,
                intent_score=score.intent_score,
                urgency_score=score.urgency_score,
                opportunity_score=score.opportunity_score,
                spam_score=score.spam_score,
                overall_score=score.overall_lead_score,
                explanation_json=json.dumps(explanation, ensure_ascii=False),
                next_best_action=score.next_best_action.value,
            )
        )
        comment_ids = set()
        for comment in (comments or {}).get(raw.external_id, []):
            ph = PhoneNormalizer.extract_and_normalize_all(
                comment.content, source_type="SOCIAL_COMMENT", source_url=raw.url
            )
            cs = lead_scorer.score_post(
                comment.content,
                ph[0].normalized_phone if ph else None,
                comment.author_name,
            )
            if comment.external_id in comment_ids:
                continue
            comment_ids.add(comment.external_id)
            db.add(
                SocialCommentDB(
                    post_id=post.id,
                    **comment.model_dump(),
                    detected_phone=ph[0].normalized_phone if ph else None,
                    intent_score=cs.intent_score,
                )
            )
        job.matched_count += 1
        if score.overall_lead_score >= 55 and score.spam_score < 60:
            job.qualified_count += 1
        if score.spam_score >= 60:
            job.spam_count += 1
        dedup.record_seen(
            raw.platform,
            raw.external_id,
            dedup.compute_canonical_hash(raw.platform, author_key, raw.content, stamp),
        )
        accepted.append(post.id)
    db.flush()
    return accepted
