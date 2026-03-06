import uuid
from datetime import datetime

from pydantic import BaseModel


class TrafficSummary(BaseModel):
    traffic_used: int
    traffic_limit: int
    traffic_up: int
    traffic_down: int
    usage_percent: float


class KeyTrafficResponse(BaseModel):
    key_id: uuid.UUID
    traffic_up: int
    traffic_down: int
    is_active: bool


class TrafficHistoryPoint(BaseModel):
    timestamp: datetime
    bytes_up: int
    bytes_down: int
    upload_speed: float
    download_speed: float


class SpeedUpdate(BaseModel):
    timestamp: float
    upload_speed_mbps: float
    download_speed_mbps: float
    upload_total_gb: float
    download_total_gb: float
