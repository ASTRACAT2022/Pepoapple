import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Device, Squad, User, UserStatus
from app.schemas.devices import DeviceRegisterRequest, DeviceResponse
from app.schemas.users import UserCreate, UserLimitUpdate, UserListResponse, UserResponse
from app.services.audit import write_audit
from app.services.auth import AuthContext, get_auth_context
from app.services.devices import register_device, reset_devices
from app.services.rbac import require_scopes
from app.services.webhooks import enqueue_event

router = APIRouter(prefix="/users", tags=["users"])


def _enforce_user_visibility(user: User, ctx: AuthContext) -> None:
    if ctx.reseller_id and user.reseller_id != ctx.reseller_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")


@router.post("", response_model=UserResponse, dependencies=[Depends(require_scopes("users.write"))])
def create_user(payload: UserCreate, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> User:
    data = payload.model_dump()
    if ctx.reseller_id:
        data["reseller_id"] = ctx.reseller_id

    user = User(**data)
    db.add(user)
    db.flush()
    write_audit(db, ctx.principal_id, "user.created", "user", user.id, {"uuid": user.uuid})
    db.commit()
    db.refresh(user)

    enqueue_event(db, "user.created", {"user_id": user.id, "uuid": user.uuid, "status": user.status.value})
    return user


@router.get("", response_model=UserListResponse, dependencies=[Depends(require_scopes("users.read"))])
def list_users(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    status_filter: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> UserListResponse:
    sortable_columns = {
        "created_at": User.created_at,
        "traffic_used_bytes": User.traffic_used_bytes,
        "expires_at": User.expires_at,
    }
    order_col = sortable_columns.get(sort_by, User.created_at)
    order_exp = asc(order_col) if sort_order == "asc" else desc(order_col)

    query = select(User)
    if status_filter:
        query = query.where(User.status == status_filter)
    if ctx.reseller_id:
        query = query.where(User.reseller_id == ctx.reseller_id)

    items = db.scalars(query.order_by(order_exp).offset(offset).limit(limit)).all()

    total_query = select(User)
    if status_filter:
        total_query = total_query.where(User.status == status_filter)
    if ctx.reseller_id:
        total_query = total_query.where(User.reseller_id == ctx.reseller_id)
    total = len(db.scalars(total_query).all())
    return UserListResponse(items=items, total=total)


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_scopes("users.read"))])
def get_user(user_id: str, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)
    return user


@router.patch("/{user_id}/block", response_model=UserResponse, dependencies=[Depends(require_scopes("users.write"))])
def block_user(user_id: str, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)
    user.status = UserStatus.blocked
    write_audit(db, ctx.principal_id, "user.blocked", "user", user.id)
    db.commit()
    db.refresh(user)
    enqueue_event(db, "user.blocked", {"user_id": user.id})
    return user


@router.patch("/{user_id}/limits", response_model=UserResponse, dependencies=[Depends(require_scopes("users.write"))])
def update_limits(user_id: str, payload: UserLimitUpdate, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)

    user.traffic_limit_bytes = payload.traffic_limit_bytes
    if payload.max_devices is not None:
        user.max_devices = payload.max_devices

    write_audit(db, ctx.principal_id, "user.limits_updated", "user", user.id, payload.model_dump())
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/{user_id}/reset-subscription",
    response_model=UserResponse,
    dependencies=[Depends(require_scopes("users.write"))],
)
def reset_subscription(user_id: str, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)

    user.expires_at = datetime.now(timezone.utc)
    user.traffic_used_bytes = 0
    user.status = UserStatus.expired
    write_audit(db, ctx.principal_id, "user.subscription_reset", "user", user.id)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/rotate-keys", response_model=UserResponse, dependencies=[Depends(require_scopes("users.write"))])
def rotate_keys(user_id: str, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)

    user.uuid = str(uuid.uuid4())
    user.vless_id = str(uuid.uuid4())
    user.short_id = uuid.uuid4().hex[:8]
    write_audit(db, ctx.principal_id, "user.keys_rotated", "user", user.id)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/assign-squad", response_model=UserResponse, dependencies=[Depends(require_scopes("users.write"))])
def assign_squad(user_id: str, squad_id: str, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)

    squad = db.get(Squad, squad_id)
    if not squad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="squad_not_found")

    user.squad_id = squad.id
    write_audit(db, ctx.principal_id, "user.squad_assigned", "user", user.id, {"squad_id": squad.id})
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/devices", response_model=list[DeviceResponse], dependencies=[Depends(require_scopes("users.read"))])
def list_devices(user_id: str, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> list[Device]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)
    return db.scalars(select(Device).where(Device.user_id == user.id).order_by(Device.last_seen_at.desc())).all()


@router.post(
    "/{user_id}/devices/register",
    response_model=DeviceResponse,
    dependencies=[Depends(require_scopes("users.write"))],
)
def register_user_device(
    user_id: str,
    payload: DeviceRegisterRequest,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> Device:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)
    return register_device(db, user, payload.device_hash)


@router.post("/{user_id}/devices/reset", dependencies=[Depends(require_scopes("users.write"))])
def reset_user_devices(user_id: str, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)

    reset_count = reset_devices(db, user)
    write_audit(db, ctx.principal_id, "user.devices_reset", "user", user.id, {"count": reset_count})
    return {"ok": True, "reset_count": reset_count}


@router.delete("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_scopes("users.write"))])
def soft_delete_user(user_id: str, db: Session = Depends(get_db), ctx: AuthContext = Depends(get_auth_context)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    _enforce_user_visibility(user, ctx)

    user.status = UserStatus.deleted
    write_audit(db, ctx.principal_id, "user.deleted", "user", user.id)
    db.commit()
    db.refresh(user)
    return user
