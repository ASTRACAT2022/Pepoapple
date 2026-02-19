from datetime import datetime

from pydantic import BaseModel


class BackupRunRequest(BaseModel):
    storage_type: str = "local"


class BackupSnapshotResponse(BaseModel):
    id: str
    storage_type: str
    file_path: str
    status: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}
