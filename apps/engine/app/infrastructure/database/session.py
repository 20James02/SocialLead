import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

Base = declarative_base()

# Configure SQLite engine with WAL mode and foreign key constraint enforcement
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def recover_interrupted_operations():
    from datetime import datetime, timezone
    from app.infrastructure.database.models import ScanJobDB, CampaignRecipientDB

    with SessionLocal() as db:
        db.query(ScanJobDB).filter(ScanJobDB.status.in_(["RUNNING", "PAUSED"])).update(
            {
                "status": "FAILED",
                "error_message": "Engine restarted or restored before scan completed",
                "finished_at": datetime.now(timezone.utc),
            }
        )
        db.query(CampaignRecipientDB).filter(
            CampaignRecipientDB.status == "SENDING"
        ).update({"status": "UNKNOWN"})
        db.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Additive migration for databases produced by the initial prototype.
    with engine.begin() as conn:
        columns = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(scan_jobs)")}
        if "error_message" not in columns:
            conn.exec_driver_sql("ALTER TABLE scan_jobs ADD COLUMN error_message TEXT")
        post_columns = {
            r[1] for r in conn.exec_driver_sql("PRAGMA table_info(social_posts)")
        }
        if "canonical_hash" not in post_columns:
            conn.exec_driver_sql(
                "ALTER TABLE social_posts ADD COLUMN canonical_hash TEXT"
            )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_social_posts_canonical_hash ON social_posts(canonical_hash)"
        )
        comment_columns = {
            r[1] for r in conn.exec_driver_sql("PRAGMA table_info(social_comments)")
        }
        if "author_id" not in comment_columns:
            conn.exec_driver_sql(
                "ALTER TABLE social_comments ADD COLUMN author_id TEXT"
            )
        from app.modules.scanner.deduplicator import PostDeduplicator
        from app.modules.crm.care_service import to_utc
        from datetime import datetime

        for row in conn.exec_driver_sql(
            "SELECT id, platform, author_id, author_url, author_name, content, posted_at FROM social_posts WHERE canonical_hash IS NULL"
        ).fetchall():
            stamp = to_utc(datetime.fromisoformat(row[6])).isoformat()
            chash = PostDeduplicator.compute_canonical_hash(
                row[1], row[2] or row[3] or row[4], row[5], stamp
            )
            conn.exec_driver_sql(
                "UPDATE social_posts SET canonical_hash = ? WHERE id = ?",
                (chash, row[0]),
            )
