from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, DeviceEvictionPolicy, User


def register_device(db: Session, user: User, device_hash: str) -> Device:
    now = datetime.now(timezone.utc)
    existing = db.scalar(
        select(Device).where(Device.user_id == user.id, Device.device_hash == device_hash, Device.is_active.is_(True))
    )
    if existing:
        existing.last_seen_at = now
        db.commit()
        db.refresh(existing)
        return existing

    active_devices = db.scalars(
        select(Device).where(Device.user_id == user.id, Device.is_active.is_(True)).order_by(Device.first_seen_at.asc())
    ).all()

    if user.max_devices > 0 and len(active_devices) >= user.max_devices:
        policy = user.device_eviction_policy
        if policy == DeviceEvictionPolicy.reject:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="max_devices_reached")
        oldest = active_devices[0]
        oldest.is_active = False

    device = Device(user_id=user.id, device_hash=device_hash, first_seen_at=now, last_seen_at=now, is_active=True)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def reset_devices(db: Session, user: User) -> int:
    devices = db.scalars(select(Device).where(Device.user_id == user.id, Device.is_active.is_(True))).all()
    for device in devices:
        device.is_active = False
    db.commit()
    return len(devices)
