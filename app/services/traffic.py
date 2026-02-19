from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Node, NodeStatus, NodeUsage, User, UserStatus
from app.services.audit import write_audit
from app.services.devices import register_device
from app.services.webhooks import enqueue_event


def report_usage(
    db: Session, node_token: str, user_uuid: str, bytes_used: int, device_hash: Optional[str] = None
) -> None:
    node = db.scalar(select(Node).where(Node.node_token == node_token))
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="node_not_found")

    user = db.scalar(select(User).where(User.uuid == user_uuid))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    if user.strict_bind:
        if not device_hash:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="device_hash_required")
        register_device(db, user, device_hash)
    elif device_hash:
        register_device(db, user, device_hash)

    usage = NodeUsage(node_id=node.id, user_id=user.id, bytes_used=bytes_used)
    user.traffic_used_bytes += bytes_used

    if user.traffic_limit_bytes > 0 and user.traffic_used_bytes >= user.traffic_limit_bytes:
        user.status = UserStatus.blocked
        write_audit(
            db,
            actor="system",
            action="traffic.limit_reached",
            entity_type="user",
            entity_id=user.id,
            payload={"used": user.traffic_used_bytes, "limit": user.traffic_limit_bytes},
        )
        enqueue_event(
            db,
            "traffic.limit_reached",
            {"user_id": user.id, "used": user.traffic_used_bytes, "limit": user.traffic_limit_bytes},
            auto_commit=False,
        )

    node.status = NodeStatus.online
    db.add(usage)
    db.commit()
