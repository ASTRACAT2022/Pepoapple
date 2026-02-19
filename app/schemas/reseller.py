from datetime import datetime

from pydantic import BaseModel


class ResellerCreate(BaseModel):
    name: str
    description: str = ""


class ResellerResponse(BaseModel):
    id: str
    name: str
    description: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
