import uuid
from datetime import datetime

from pydantic import BaseModel


class AdminInstanceResponse(BaseModel):
    id: uuid.UUID
    ss_port: int
    server_id: uuid.UUID
    server_name: str | None
    server_country: str | None
    user_email: str
    started_at: datetime | None
    uptime_seconds: int | None
    traffic_up: int
    traffic_down: int
    current_upload_bps: float
    current_download_bps: float
    is_alive: bool


class SpeedPoint(BaseModel):
    timestamp: datetime
    upload_speed: float
    download_speed: float