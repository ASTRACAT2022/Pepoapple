from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session, actor: str, action: str, entity_type: str, entity_id: str, payload: Optional[dict] = None
) -> None:
    record = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id or "pending",
        payload=payload or {},
    )
    db.add(record)
