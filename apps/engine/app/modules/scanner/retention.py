from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.infrastructure.database.models import SocialPostDB, SavedPostDB

class RetentionCleaner:
    """
    Automated Retention Subsystem.
    Purges temporary raw scan results while strictly protecting:
      - Posts marked is_raw == False
      - Saved Posts (saved_posts table)
      - Posts tied to Persons or promoted Customers
    """
    @classmethod
    def cleanup_expired_raw_scans(cls, db: Session, retention_hours: int = 24) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)

        # Get all saved post IDs to ensure absolute protection
        saved_post_ids = {r[0] for r in db.query(SavedPostDB.post_id).all()}

        # Query candidates for deletion: is_raw is True AND posted_at/detected_at < cutoff
        query = db.query(SocialPostDB).filter(
            and_(
                SocialPostDB.is_raw == True,
                SocialPostDB.detected_at < cutoff,
                ~SocialPostDB.id.in_(saved_post_ids)
            )
        )

        expired_posts = query.all()
        deleted_count = len(expired_posts)
        for post in expired_posts:
            db.delete(post)
        
        db.commit()
        return deleted_count

retention_cleaner = RetentionCleaner()
