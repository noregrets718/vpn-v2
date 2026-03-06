import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TrafficLog(Base):
    __tablename__ = "traffic_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    access_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("access_keys.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    bytes_up: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    bytes_down: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    upload_speed: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    download_speed: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    access_key = relationship("AccessKey", back_populates="traffic_logs")
