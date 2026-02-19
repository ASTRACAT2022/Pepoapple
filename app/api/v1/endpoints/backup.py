from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import BackupSnapshot
from app.schemas.backup import BackupRunRequest, BackupSnapshotResponse
from app.services.backup import run_backup
from app.services.rbac import require_scopes

router = APIRouter(prefix="/backups", tags=["backups"])


@router.post("/run", response_model=BackupSnapshotResponse, dependencies=[Depends(require_scopes("api.manage"))])
def run_backup_now(payload: BackupRunRequest, db: Session = Depends(get_db)) -> BackupSnapshot:
    return run_backup(db, payload.storage_type)


@router.get("", response_model=list[BackupSnapshotResponse], dependencies=[Depends(require_scopes("api.manage"))])
def list_backups(db: Session = Depends(get_db)) -> list[BackupSnapshot]:
    return db.scalars(select(BackupSnapshot).order_by(desc(BackupSnapshot.created_at))).all()
