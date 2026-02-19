from pydantic import BaseModel, Field


class SquadCreate(BaseModel):
    name: str
    description: str = ""
    selection_policy: str = "round-robin"
    fallback_policy: str = "none"
    allowed_protocols: list[str] = Field(default_factory=lambda: ["AWG2", "Sing-box"])


class SquadResponse(BaseModel):
    id: str
    name: str
    description: str
    selection_policy: str
    fallback_policy: str
    allowed_protocols: list[str]

    model_config = {"from_attributes": True}


class ServerCreate(BaseModel):
    host: str
    ip: str = ""
    provider: str = ""
    region: str = ""
    squad_id: str
    price: float = 0
    currency: str = "USD"


class ServerResponse(BaseModel):
    id: str
    host: str
    ip: str
    provider: str
    region: str
    squad_id: str
    status: str

    model_config = {"from_attributes": True}
