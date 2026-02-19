from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WebhookEndpointCreate(BaseModel):
    name: str
    target_url: str
    secret: str
    events: list[str] = Field(default_factory=list)


class WebhookEndpointResponse(BaseModel):
    id: str
    name: str
    target_url: str
    events: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookDeliveryResponse(BaseModel):
    id: str
    endpoint_id: str
    event: str
    status: str
    attempts: int
    response_status: Optional[int]
    last_error: str
    created_at: datetime
    sent_at: Optional[datetime]

    model_config = {"from_attributes": True}
