from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PlanCreate(BaseModel):
    name: str
    price: float
    currency: str = "USD"
    duration_days: int = 30
    traffic_limit_bytes: int = 0
    max_devices: int = 1


class PlanResponse(BaseModel):
    id: str
    name: str
    price: float
    currency: str
    duration_days: int
    traffic_limit_bytes: int
    max_devices: int
    is_active: bool

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    user_id: str
    plan_id: str


class OrderResponse(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: str
    total_amount: float
    currency: str
    created_at: datetime
    paid_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PaymentConfirm(BaseModel):
    order_id: str
    external_payment_id: str
    provider: str = "manual"


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    provider: str
    external_payment_id: str
    status: str
    amount: float
    currency: str

    model_config = {"from_attributes": True}
