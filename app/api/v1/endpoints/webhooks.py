from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import WebhookDelivery, WebhookEndpoint
from app.schemas.webhooks import WebhookDeliveryResponse, WebhookEndpointCreate, WebhookEndpointResponse
from app.services.audit import write_audit
from app.services.auth import AuthContext, get_auth_context
from app.services.rbac import require_scopes
from app.services.webhooks import deliver_pending

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/endpoints", response_model=WebhookEndpointResponse, dependencies=[Depends(require_scopes("api.manage"))])
def create_endpoint(
    payload: WebhookEndpointCreate,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> WebhookEndpoint:
    endpoint = WebhookEndpoint(**payload.model_dump())
    db.add(endpoint)
    db.flush()
    write_audit(db, ctx.principal_id, "webhook.endpoint_created", "webhook_endpoint", endpoint.id)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.get("/endpoints", response_model=list[WebhookEndpointResponse], dependencies=[Depends(require_scopes("api.manage"))])
def list_endpoints(db: Session = Depends(get_db)) -> list[WebhookEndpoint]:
    return db.scalars(select(WebhookEndpoint).order_by(desc(WebhookEndpoint.created_at))).all()


@router.post("/process", dependencies=[Depends(require_scopes("api.manage"))])
def process_deliveries(limit: int = 100, db: Session = Depends(get_db)) -> dict:
    return deliver_pending(db, limit=limit)


@router.get("/deliveries", response_model=list[WebhookDeliveryResponse], dependencies=[Depends(require_scopes("api.manage"))])
def list_deliveries(db: Session = Depends(get_db)) -> list[WebhookDelivery]:
    return db.scalars(select(WebhookDelivery).order_by(desc(WebhookDelivery.created_at)).limit(500)).all()
