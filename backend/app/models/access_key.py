import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint


class AccessKey(Base):
    __tablename__ = "access_keys"
    __table_args__ = (UniqueConstraint("server_id", "ss_port"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=False)
    ss_port: Mapped[int] = mapped_column(Integer, nullable=False)
    ss_password: Mapped[str] = mapped_column(String(255), nullable=False)
    ss_method: Mapped[str] = mapped_column(String(50), default="chacha20-ietf-poly1305", nullable=False)
    traffic_up: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    traffic_down: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="access_keys")
    server = relationship("Server", back_populates="access_keys", lazy="selectin")
    traffic_logs = relationship("TrafficLog", back_populates="access_key", lazy="selectin")
