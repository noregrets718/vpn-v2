import enum
import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class PlanType(str, enum.Enum):
    free = "free"
    basic = "basic"
    pro = "pro"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[PlanType] = mapped_column(Enum(PlanType), default=PlanType.free, nullable=False)
    traffic_limit: Mapped[int] = mapped_column(BigInteger, default=5_368_709_120, nullable=False)  # 5 GB
    traffic_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    access_keys = relationship("AccessKey", back_populates="user", lazy="selectin")
