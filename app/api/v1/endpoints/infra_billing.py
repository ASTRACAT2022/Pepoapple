from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.db.session import get_db
from app.models import Server
from app.services.rbac import require_scopes

router = APIRouter(prefix="/infra-billing", tags=["infra-billing"])


@router.get("/report", dependencies=[Depends(require_scopes("infra.billing.read"))])
def report(db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(Server.provider, Server.currency, func.count(Server.id), func.coalesce(func.sum(Server.price), 0)).group_by(
            Server.provider, Server.currency
        )
    ).all()
    items = [
        {
            "provider": provider,
            "currency": currency,
            "servers": servers,
            "monthly_total": float(total),
        }
        for provider, currency, servers, total in rows
    ]
    due_rows = db.scalars(select(Server).where(Server.next_due_at.is_not(None)).order_by(Server.next_due_at.asc()).limit(100)).all()
    due_items = [
        {
            "server_id": server.id,
            "host": server.host,
            "next_due_at": server.next_due_at,
            "infra_status": server.infra_status,
            "reminder_days_before": server.reminder_days_before,
        }
        for server in due_rows
    ]
    return {"items": items, "due": due_items}
