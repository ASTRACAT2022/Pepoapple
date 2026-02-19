from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BootstrapAdminRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=list)
    reseller_id: Optional[str] = None


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    scopes: list[str]


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    status: str
    reseller_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
