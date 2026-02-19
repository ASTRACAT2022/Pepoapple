from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.db.session import get_db
from app.models import Node, NodeUsage, User
from app.services.rbac import require_scopes

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", dependencies=[Depends(require_scopes("billing.read"))])
def overview(db: Session = Depends(get_db)) -> dict:
    users_total = len(db.scalars(select(User.id)).all())
    users_active = len(db.scalars(select(User.id).where(User.status == "active")).all())
    nodes_total = len(db.scalars(select(Node.id)).all())
    nodes_online = len(db.scalars(select(Node.id).where(Node.status == "online")).all())
    total_traffic = db.scalar(select(func.coalesce(func.sum(NodeUsage.bytes_used), 0))) or 0

    per_day_rows = db.execute(
        select(func.date(NodeUsage.reported_at), func.coalesce(func.sum(NodeUsage.bytes_used), 0))
        .group_by(func.date(NodeUsage.reported_at))
        .order_by(func.date(NodeUsage.reported_at))
        .limit(30)
    ).all()
    traffic_per_day = [{"day": str(day), "bytes": int(total)} for day, total in per_day_rows]

    return {
        "users": {"total": users_total, "active": users_active},
        "nodes": {"total": nodes_total, "online": nodes_online},
        "traffic": {"total_bytes": int(total_traffic), "per_day": traffic_per_day},
    }
