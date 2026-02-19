from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    uuid: str
    vless_id: str
    short_id: str
    squad_id: Optional[str] = None
    traffic_limit_bytes: int = 0
    max_devices: int = 1
    hwid_policy: str = "none"
    strict_bind: bool = False
    device_eviction_policy: str = "reject"
    subscription_token: str
    external_identities: dict = Field(default_factory=dict)
    reseller_id: Optional[str] = None


class UserLimitUpdate(BaseModel):
    traffic_limit_bytes: int
    max_devices: Optional[int] = None


class UserResponse(BaseModel):
    id: str
    uuid: str
    vless_id: str
    short_id: str
    status: str
    traffic_limit_bytes: int
    traffic_used_bytes: int
    expires_at: Optional[datetime]
    max_devices: int
    hwid_policy: str
    strict_bind: bool
    device_eviction_policy: str
    squad_id: Optional[str]
    reseller_id: Optional[str]
    subscription_token: str

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
