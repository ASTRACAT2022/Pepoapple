from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProtocolProfileCreate(BaseModel):
    name: str
    protocol_type: str
    profile_schema: dict = Field(default_factory=dict, alias="schema_json")

    model_config = ConfigDict(populate_by_name=True)


class ProtocolProfileResponse(BaseModel):
    id: str
    name: str
    protocol_type: str
    profile_schema: dict = Field(alias="schema_json")
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
