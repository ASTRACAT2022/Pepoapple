import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BackupSnapshot, Node, Plan, Server, Squad, User

settings = get_settings()


def run_backup(db: Session, storage_type: str = "local") -> BackupSnapshot:
    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    file_path = backup_dir / f"pepoapple-backup-{ts}.json"

    payload = {
        "users": [
            {
                "id": user.id,
                "uuid": user.uuid,
                "subscription_token": user.subscription_token,
                "status": user.status.value,
                "traffic_limit_bytes": user.traffic_limit_bytes,
                "traffic_used_bytes": user.traffic_used_bytes,
            }
            for user in db.scalars(select(User)).all()
        ],
        "squads": [{"id": squad.id, "name": squad.name} for squad in db.scalars(select(Squad)).all()],
        "servers": [{"id": server.id, "host": server.host, "squad_id": server.squad_id} for server in db.scalars(select(Server)).all()],
        "nodes": [{"id": node.id, "server_id": node.server_id, "desired_config_revision": node.desired_config_revision} for node in db.scalars(select(Node)).all()],
        "plans": [{"id": plan.id, "name": plan.name, "price": plan.price} for plan in db.scalars(select(Plan)).all()],
        "created_at": ts,
    }

    raw = json.dumps(payload, ensure_ascii=True, indent=2)
    file_path.write_text(raw, encoding="utf-8")
    snapshot = BackupSnapshot(
        storage_type=storage_type,
        file_path=str(file_path),
        status="created",
        size_bytes=os.path.getsize(file_path),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
