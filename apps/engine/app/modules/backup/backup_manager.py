import sqlite3
import shutil
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from app.core.config import settings


class BackupManager:
    """
    Manages local database backups using SQLite Online Backup API.
    Guarantees consistent, non-locking snapshots without corrupting active WAL transactions.
    """

    BACKUP_DIR = settings.DATA_DIR / "backups"

    @classmethod
    def create_backup(cls) -> Dict[str, Any]:
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        backup_filename = f"scansocial_backup_{timestamp}.bak"
        backup_path = cls.BACKUP_DIR / backup_filename

        src_conn = sqlite3.connect(str(settings.DATABASE_PATH))
        dst_conn = sqlite3.connect(str(backup_path))

        try:
            with dst_conn:
                src_conn.backup(dst_conn, pages=100)
        finally:
            src_conn.close()
            dst_conn.close()

        # Compute SHA256 checksum
        checksum = hashlib.sha256(backup_path.read_bytes()).hexdigest()
        file_size = backup_path.stat().st_size

        return {
            "filename": backup_filename,
            "filepath": str(backup_path),
            "size_bytes": file_size,
            "sha256": checksum,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def verify_backup_integrity(cls, backup_path: Path) -> bool:
        if not backup_path.exists():
            return False
        try:
            conn = sqlite3.connect(
                f"{backup_path.resolve().as_uri()}?mode=ro", uri=True
            )
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            conn.close()
            return res and res[0] == "ok"
        except Exception:
            return False


backup_manager = BackupManager()
