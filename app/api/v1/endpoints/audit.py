from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AuditLog
from app.services.rbac import require_scopes

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", dependencies=[Depends(require_scopes("users.read"))])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)

    items = db.scalars(query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)).all()
    return {
        "items": [
            {
                "id": item.id,
                "actor": item.actor,
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "payload": item.payload,
                "created_at": item.created_at,
            }
            for item in items
        ]
    }
