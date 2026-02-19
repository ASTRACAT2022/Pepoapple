from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Order, OrderStatus, Plan, User
from app.schemas.billing import (
    OrderCreate,
    OrderResponse,
    PaymentConfirm,
    PaymentResponse,
    PlanCreate,
    PlanResponse,
)
from app.services.audit import write_audit
from app.services.billing import confirm_payment_and_activate
from app.services.rbac import require_scopes
from app.services.webhooks import enqueue_event

router = APIRouter(tags=["billing"])


@router.post("/plans", response_model=PlanResponse, dependencies=[Depends(require_scopes("billing.write"))])
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)) -> Plan:
    plan = Plan(**payload.model_dump())
    db.add(plan)
    write_audit(db, "billing", "plan.created", "plan", plan.id, payload.model_dump())
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/plans", response_model=list[PlanResponse], dependencies=[Depends(require_scopes("billing.read"))])
def list_plans(db: Session = Depends(get_db)) -> list[Plan]:
    return db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price)).all()


@router.post("/orders", response_model=OrderResponse, dependencies=[Depends(require_scopes("billing.write"))])
def create_order(
    payload: OrderCreate,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> Order:
    user = db.get(User, payload.user_id)
    plan = db.get(Plan, payload.plan_id)
    if not user or not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_or_plan_not_found")

    if idempotency_key:
        existing = db.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
        if existing:
            return existing

    order = Order(
        user_id=user.id,
        plan_id=plan.id,
        total_amount=plan.price,
        currency=plan.currency,
        status=OrderStatus.pending,
        idempotency_key=idempotency_key,
    )
    db.add(order)
    write_audit(db, "billing", "order.created", "order", order.id, {"user_id": user.id, "plan_id": plan.id})
    db.commit()
    db.refresh(order)
    return order


@router.post("/payments/confirm", response_model=PaymentResponse, dependencies=[Depends(require_scopes("billing.write"))])
def confirm_payment(payload: PaymentConfirm, db: Session = Depends(get_db)) -> PaymentResponse:
    payment = confirm_payment_and_activate(db, payload.order_id, payload.external_payment_id, payload.provider)
    enqueue_event(db, "order.paid", {"order_id": payload.order_id, "payment_id": payment.id})
    return payment


@router.get("/orders/{order_id}", response_model=OrderResponse, dependencies=[Depends(require_scopes("billing.read"))])
def get_order(order_id: str, db: Session = Depends(get_db)) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    return order
