import uuid
from datetime import datetime

from pydantic import BaseModel


class ServerCreate(BaseModel):
    name: str
    ip_address: str | None = None
    port: int | None = None
    username: str
    password: str
    country: str
    city: str | None = None
    port_range_start: int = 10001
    port_range_end: int = 60000
    is_local: bool = True
    agent_url: str | None = None
    agent_token: str | None = None


class ServerUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    city: str | None = None
    is_active: bool | None = None
    ssh_user: str | None = None
    ssh_port: int | None = None
    ssh_key_path: str | None = None


class ServerResponse(BaseModel):
    id: uuid.UUID
    name: str
    ip_address: str
    country: str
    city: str | None
    is_active: bool
    current_load: int
    connected_users: int
    created_at: datetime

    model_config = {"from_attributes": True}
