from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Order, OrderStatus, Payment, PaymentStatus, Plan, User, UserStatus
from app.services.audit import write_audit


def confirm_payment_and_activate(db: Session, order_id: str, external_payment_id: str, provider: str) -> Payment:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")

    if order.status == OrderStatus.paid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="order_already_paid")

    user = db.get(User, order.user_id)
    plan = db.get(Plan, order.plan_id)
    if not user or not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="order_inconsistent")

    payment = Payment(
        order_id=order.id,
        provider=provider,
        external_payment_id=external_payment_id,
        status=PaymentStatus.succeeded,
        amount=order.total_amount,
        currency=order.currency,
    )

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.paid
    order.paid_at = now

    base = user.expires_at if user.expires_at and user.expires_at > now else now
    user.expires_at = base + timedelta(days=plan.duration_days)
    user.traffic_limit_bytes = plan.traffic_limit_bytes
    user.max_devices = plan.max_devices
    user.status = UserStatus.active

    db.add(payment)
    db.flush()
    write_audit(
        db,
        actor="billing",
        action="payment.confirmed",
        entity_type="order",
        entity_id=order.id,
        payload={"payment_id": payment.id, "user_id": user.id},
    )
    db.commit()
    db.refresh(payment)
    return payment
