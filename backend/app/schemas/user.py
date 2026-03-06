import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import PlanType


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    plan: PlanType
    traffic_used: int
    traffic_limit: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
