from datetime import datetime

from pydantic import BaseModel


class DeviceRegisterRequest(BaseModel):
    device_hash: str


class DeviceResponse(BaseModel):
    id: str
    user_id: str
    device_hash: str
    is_active: bool
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}
