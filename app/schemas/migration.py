from pydantic import BaseModel, Field


class MigrationRunRequest(BaseModel):
    mode: str
    payload: dict = Field(default_factory=dict)


class MigrationRunResponse(BaseModel):
    id: str
    mode: str
    status: str
    details: dict

    model_config = {"from_attributes": True}


class LegacyTokenMapCreate(BaseModel):
    user_id: str
    legacy_token: str
    subscription_token: str
