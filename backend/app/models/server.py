import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    port_range_start: Mapped[int] = mapped_column(Integer, default=10001, nullable=False)
    port_range_end: Mapped[int] = mapped_column(Integer, default=60000, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_local: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_load: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bandwidth_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    connected_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agent_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssh_user: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ssh_port: Mapped[int | None] = mapped_column(Integer, nullable=True, default=22)
    ssh_key_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    access_keys = relationship("AccessKey", back_populates="server", lazy="selectin")
