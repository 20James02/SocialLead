from fastapi import APIRouter, Depends
from app.api.deps import SessionAuth
from app.modules.backup.backup_manager import backup_manager

router = APIRouter(prefix="/backup", tags=["Backup & Restore"], dependencies=[SessionAuth])

@router.post("/create")
def create_backup():
    result = backup_manager.create_backup()
    return {"status": "SUCCESS", "backup": result}
