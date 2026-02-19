import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import WebhookDelivery, WebhookDeliveryStatus, WebhookEndpoint

settings = get_settings()


def enqueue_event(db: Session, event: str, payload: dict, auto_commit: bool = True) -> list[WebhookDelivery]:
    endpoints = db.scalars(
        select(WebhookEndpoint).where(WebhookEndpoint.is_active.is_(True)).order_by(WebhookEndpoint.created_at.asc())
    ).all()
    deliveries = []
    for endpoint in endpoints:
        if endpoint.events and event not in endpoint.events:
            continue
        delivery = WebhookDelivery(endpoint_id=endpoint.id, event=event, payload=payload)
        deliveries.append(delivery)
        db.add(delivery)
    if auto_commit:
        db.commit()
    return deliveries


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def deliver_pending(db: Session, limit: int = 100) -> dict:
    pending = db.scalars(
        select(WebhookDelivery).where(WebhookDelivery.status == WebhookDeliveryStatus.pending).order_by(WebhookDelivery.created_at).limit(limit)
    ).all()

    sent = 0
    failed = 0
    with httpx.Client(timeout=settings.webhook_timeout_seconds) as client:
        for item in pending:
            endpoint = db.get(WebhookEndpoint, item.endpoint_id)
            if not endpoint or not endpoint.is_active:
                item.status = WebhookDeliveryStatus.failed
                item.last_error = "endpoint_inactive"
                item.attempts += 1
                failed += 1
                continue

            raw_body = json.dumps(item.payload).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "X-Pepoapple-Event": item.event,
                "X-Pepoapple-Signature": _signature(endpoint.secret, raw_body),
            }
            try:
                response = client.post(endpoint.target_url, content=raw_body, headers=headers)
                item.response_status = response.status_code
                item.attempts += 1
                if 200 <= response.status_code < 300:
                    item.status = WebhookDeliveryStatus.sent
                    item.sent_at = datetime.now(timezone.utc)
                    sent += 1
                else:
                    item.status = WebhookDeliveryStatus.failed
                    item.last_error = f"status_{response.status_code}"
                    failed += 1
            except Exception as exc:
                item.attempts += 1
                item.status = WebhookDeliveryStatus.failed
                item.last_error = str(exc)
                failed += 1

    db.commit()
    return {"processed": len(pending), "sent": sent, "failed": failed}
