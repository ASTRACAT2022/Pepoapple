from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import MigrationMode, MigrationRun, SubscriptionAlias, User
from app.schemas.migration import LegacyTokenMapCreate, MigrationRunRequest, MigrationRunResponse
from app.services.audit import write_audit
from app.services.auth import AuthContext, get_auth_context
from app.services.migration import run_migration
from app.services.rbac import require_scopes
from app.services.webhooks import enqueue_event

router = APIRouter(prefix="/migration", tags=["migration"])


@router.post("/run", response_model=MigrationRunResponse, dependencies=[Depends(require_scopes("migration.run"))])
def run_migration_job(
    payload: MigrationRunRequest,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> MigrationRun:
    try:
        mode = MigrationMode(payload.mode)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_mode") from err

    record = run_migration(db, mode, payload.payload)
    write_audit(db, ctx.principal_id, "migration.completed", "migration_run", record.id, {"mode": mode.value})
    enqueue_event(db, "migration.completed", {"migration_run_id": record.id, "status": record.status.value})
    return record


@router.post("/legacy-token-map", dependencies=[Depends(require_scopes("migration.run"))])
def create_legacy_map(
    payload: LegacyTokenMapCreate,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> dict:
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    mapping = SubscriptionAlias(**payload.model_dump())
    db.add(mapping)
    db.flush()
    write_audit(
        db,
        ctx.principal_id,
        "legacy_token.mapped",
        "subscription_alias",
        mapping.id,
        {"legacy_token": mapping.legacy_token},
    )
    db.commit()
    return {"ok": True}


@router.get("/runs", response_model=list[MigrationRunResponse], dependencies=[Depends(require_scopes("migration.run"))])
def list_runs(db: Session = Depends(get_db)) -> list[MigrationRun]:
    return db.scalars(select(MigrationRun).order_by(MigrationRun.created_at.desc())).all()
