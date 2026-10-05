from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from app.core.config import settings
from app.infrastructure.database.session import (
    engine,
    Base,
    init_db,
    SessionLocal,
    recover_interrupted_operations,
)
from app.infrastructure.database.models import ScanJobDB
from app.infrastructure.fts.fts_manager import FTSManager
from app.api.deps import SessionAuth
from app.modules.backup.backup_manager import backup_manager

router = APIRouter(
    prefix="/backup", tags=["Backup & Restore"], dependencies=[SessionAuth]
)


@router.post("/create")
def create_backup():
    result = backup_manager.create_backup()
    return {"status": "SUCCESS", "backup": result}


@router.get("")
def list_backups():
    directory = backup_manager.BACKUP_DIR
    if not directory.exists():
        return []
    return [
        {
            "filename": p.name,
            "size_bytes": p.stat().st_size,
            "created_at": datetime.fromtimestamp(
                p.stat().st_mtime, timezone.utc
            ).isoformat(),
        }
        for p in sorted(directory.glob("scansocial_backup_*.bak"), reverse=True)
        if p.is_file()
    ]


class RestoreInput(BaseModel):
    filename: str = Field(min_length=1, max_length=200)


@router.post("/restore")
def restore_backup(req: RestoreInput):
    directory = backup_manager.BACKUP_DIR.resolve()
    source = (directory / req.filename).resolve()
    if (
        source.parent != directory
        or not source.name.startswith("scansocial_backup_")
        or source.suffix != ".bak"
    ):
        raise HTTPException(422, "Invalid backup filename")
    if not backup_manager.verify_backup_integrity(source):
        raise HTTPException(422, "Backup is missing or corrupt")
    with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as check:
        tables = {
            r[0]
            for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if (
            not set(Base.metadata.tables).issubset(tables)
            or check.execute("PRAGMA foreign_key_check").fetchone()
        ):
            raise HTTPException(422, "Not a valid ScanSocial CRM backup")
    with SessionLocal() as db:
        if (
            db.query(ScanJobDB)
            .filter(ScanJobDB.status.in_(["RUNNING", "PAUSED"]))
            .first()
        ):
            raise HTTPException(409, "Stop active scans before restoring data")
    safety_backup = backup_manager.create_backup()
    engine.dispose()
    try:
        with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as src:
            with sqlite3.connect(str(settings.DATABASE_PATH)) as dst:
                src.backup(dst)
        init_db()
        FTSManager.install_sync()
        recover_interrupted_operations()
    except Exception:
        # Restore the safety snapshot if migration/index setup fails.
        engine.dispose()
        with sqlite3.connect(safety_backup["filepath"]) as src:
            with sqlite3.connect(str(settings.DATABASE_PATH)) as dst:
                src.backup(dst)
        raise HTTPException(500, "Restore failed; previous data was recovered")
    return {"status": "RESTORED", "safety_backup": safety_backup["filename"]}
