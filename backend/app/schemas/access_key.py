import uuid
from datetime import datetime

from pydantic import BaseModel


class AccessKeyCreate(BaseModel):
    server_id: uuid.UUID


class AccessKeyResponse(BaseModel):
    id: uuid.UUID
    server_id: uuid.UUID
    ss_port: int
    ss_method: str
    ss_url: str | None = None
    qr_code: str | None = None
    traffic_up: int
    traffic_down: int
    is_active: bool
    created_at: datetime
    server_name: str | None = None
    server_country: str | None = None

    model_config = {"from_attributes": True}