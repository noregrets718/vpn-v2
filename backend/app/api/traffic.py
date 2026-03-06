import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_current_active_user
from app.database import get_db
from app.models.access_key import AccessKey
from app.models.traffic_log import TrafficLog
from app.models.user import User
from app.schemas.traffic import KeyTrafficResponse, TrafficHistoryPoint, TrafficSummary

router = APIRouter(prefix="/api/traffic", tags=["traffic"])

PERIOD_MAP = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


@router.get("/my", response_model=TrafficSummary)
async def my_traffic(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(AccessKey).where(AccessKey.user_id == user.id, AccessKey.is_active == True)  # noqa: E712
    )
    keys = result.scalars().all()
    total_up = sum(k.traffic_up for k in keys)
    total_down = sum(k.traffic_down for k in keys)

    usage_percent = (user.traffic_used / user.traffic_limit * 100) if user.traffic_limit > 0 else 0

    return TrafficSummary(
        traffic_used=user.traffic_used,
        traffic_limit=user.traffic_limit,
        traffic_up=total_up,
        traffic_down=total_down,
        usage_percent=round(usage_percent, 1),
    )


@router.get("/key/{key_id}", response_model=KeyTrafficResponse)
async def key_traffic(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(AccessKey).where(AccessKey.id == key_id, AccessKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    return KeyTrafficResponse(
        key_id=key.id,
        traffic_up=key.traffic_up,
        traffic_down=key.traffic_down,
        is_active=key.is_active,
    )


@router.get("/key/{key_id}/history", response_model=list[TrafficHistoryPoint])
async def key_traffic_history(
    key_id: uuid.UUID,
    period: str = Query(default="24h", regex="^(1h|24h|7d|30d)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    # Verify key ownership
    result = await db.execute(
        select(AccessKey).where(AccessKey.id == key_id, AccessKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    delta = PERIOD_MAP[period]
    since = datetime.now(timezone.utc) - delta

    result = await db.execute(
        select(TrafficLog)
        .where(TrafficLog.access_key_id == key_id, TrafficLog.timestamp >= since)
        .order_by(TrafficLog.timestamp)
    )
    logs = result.scalars().all()

    return [
        TrafficHistoryPoint(
            timestamp=log.timestamp,
            bytes_up=log.bytes_up,
            bytes_down=log.bytes_down,
            upload_speed=log.upload_speed,
            download_speed=log.download_speed,
        )
        for log in logs
    ]
