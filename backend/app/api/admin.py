import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.functions import func

from app.api.deps import get_admin_user
from app.config import settings
from app.models import User, Server, AccessKey, TrafficLog
from app.schemas.instance import AdminInstanceResponse, SpeedPoint
from app.schemas.server import AdminServerResponse
from app.schemas.user import AdminUserResponse, AdminUserUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db

import redis.asyncio as aioredis


router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            plan=u.plan,
            traffic_used=u.traffic_used,
            traffic_limit=u.traffic_limit,
            is_active=u.is_active,
            is_admin=u.is_admin,
            created_at=u.created_at,
            active_key_count=sum(1 for k in u.access_keys if k.is_active),
        )
        for u in users
    ]

@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
        user_id: uuid.UUID,
        data: AdminUserUpdate,
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
            id=user.id,
            email=user.email,
            plan=user.plan,
            traffic_used=user.traffic_used,
            traffic_limit=user.traffic_limit,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            active_key_count=sum(1 for k in user.access_keys if k.is_active),
        )


@router.get("/servers", response_model=list[AdminServerResponse])
async def list_servers(
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Server).order_by(Server.name))
    servers = result.scalars().all()
    return [
        AdminServerResponse(
            id=s.id,
            name=s.name,
            ip_address=s.ip_address,
            country=s.country,
            city=s.city,
            is_active=s.is_active,
            is_local=s.is_local,
            current_load=s.current_load,
            connected_users=s.connected_users,
            created_at=s.created_at,
            active_instances=sum(1 for k in s.access_keys if k.is_active),
        )
        for s in servers
    ]


@router.get("/instances", response_model=list[AdminInstanceResponse])
async def list_instances(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AccessKey)
        .where(
            AccessKey.is_active == True)  # noqa: E712
        .options(selectinload(AccessKey.user))
        .order_by(AccessKey.created_at.desc())
    )
    keys = result.scalars().all()

    r = aioredis.from_url(settings.REDIS_URL)
    now = datetime.now(timezone.utc)
    responses = []

    try:
        for key in keys:
            server = key.server
            user = key.user
            latest_log = max(key.traffic_logs, key=lambda l: l.timestamp, default=None)

            raw = await r.get(f"instance_alive:{key.id}")
            is_alive = None if raw is None else (raw == b"1")

            uptime = None
            if key.started_at:
                started = key.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                uptime = int((now - started).total_seconds())

            responses.append(AdminInstanceResponse(
                id=key.id,
                ss_port=key.ss_port,
                server_id=key.server_id,
                server_name=server.name if server else None,
                server_country=server.country if server else None,
                user_email=user.email if user else "unknown",
                started_at=key.started_at,
                uptime_seconds=uptime,
                traffic_up=key.traffic_up,
                traffic_down=key.traffic_down,
                current_upload_bps=latest_log.upload_speed if latest_log else 0.0,
                current_download_bps=latest_log.download_speed if latest_log else 0.0,
                is_alive=is_alive,
            ))
    finally:
        await r.aclose()

    return responses


@router.get("/instances/{key_id}/speed", response_model=list[SpeedPoint])
async def get_instance_speed(
    key_id: uuid.UUID,
    period: Literal["day", "week", "month"] = "day",  # фикс #3
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    if period == "week":
        since = now - timedelta(weeks=1)
        trunc = "hour"          # 1 точка в час → макс 168 точек
    elif period == "month":
        since = now - timedelta(days=30)
        trunc = "day"           # 1 точка в день → макс 30 точек
    else:  # "day"
        since = now - timedelta(days=1)
        trunc = "minute"        # 1 точка в минуту → макс 1440 точек

    # фикс #1 и #2 — агрегация прямо в SQL через date_trunc
    bucket = func.date_trunc(trunc, TrafficLog.timestamp).label("bucket")

    result = await db.execute(
        select(
            bucket,
            func.avg(TrafficLog.upload_speed).label("upload_speed"),
            func.avg(TrafficLog.download_speed).label("download_speed"),
        )
        .where(
            TrafficLog.access_key_id == key_id,
            TrafficLog.timestamp >= since,
        )
        .group_by(bucket)
        .order_by(bucket.asc())
    )
    rows = result.all()

    return [
        SpeedPoint(
            timestamp=row.bucket,
            upload_speed=row.upload_speed,
            download_speed=row.download_speed,
        )
        for row in rows
    ]

