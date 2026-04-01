import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.functions import func
from datetime import datetime, timezone

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models import AccessKey
from app.models.user import PlanType, User
from app.models.server import Server
from app.schemas.access_key import AccessKeyCreate, AccessKeyResponse
from app.services.shadowsocks import ss_manager
from app.services.server_backend import get_backend
from app.utils.ss_url import generate_ss_url, generate_qr_base64

router = APIRouter(prefix="/api/keys", tags=["keys"])

PLAN_KEY_LIMITS = {
    PlanType.free: 1,
    PlanType.basic: 3,
    PlanType.pro: 10,
}

@router.post("/create", response_model=AccessKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    data: AccessKeyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(func.count()).select_from(AccessKey).where(
            AccessKey.user_id == user.id, AccessKey.is_active == True  # noqa: E712
        )
    )
    active_count = result.scalar()
    limit = PLAN_KEY_LIMITS.get(user.plan, 1)
    if active_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Key limit reached for {user.plan.value} plan ({limit} keys)",
        )

    # Verify server exists
    result = await db.execute(select(Server).where(Server.id == data.server_id, Server.is_active == True))  # noqa: E712
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found or inactive")

    # Allocate port and generate password
    port = await ss_manager.get_next_free_port(db, server.id)
    password = ss_manager.generate_password()
    method = "chacha20-ietf-poly1305"

    # Start SS instance
    backend = get_backend(server)
    started = await backend.start_instance(port, password, method)
    if not started:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start VPN instance")

    # Save to DB
    key = AccessKey(
        user_id=user.id,
        server_id=server.id,
        ss_port=port,
        ss_password=password,
        ss_method=method,
        started_at=datetime.now(timezone.utc),
    )

    db.add(key)
    await db.commit()
    await db.refresh(key)

    # Generate ss:// URL and QR code
    tag = f"{server.country}-{server.name}"
    ss_url = generate_ss_url(method, password, server.ip_address, port, tag)
    qr_code = generate_qr_base64(ss_url)

    return AccessKeyResponse(
        id=key.id,
        server_id=key.server_id,
        ss_port=key.ss_port,
        ss_method=key.ss_method,
        ss_url=ss_url,
        qr_code=qr_code,
        traffic_up=key.traffic_up,
        traffic_down=key.traffic_down,
        is_active=key.is_active,
        created_at=key.created_at,
        server_name=server.name,
        server_country=server.country,
    )

@router.get("/my", response_model=list[AccessKeyResponse])
async def list_my_keys(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(AccessKey).where(AccessKey.user_id == user.id, AccessKey.is_active == True)  # noqa: E712
        .order_by(AccessKey.created_at.desc())
    )
    keys = result.scalars().all()

    responses = []
    for key in keys:
        server = key.server
        tag = f"{server.country}-{server.name}" if server else "VPN"
        host = server.ip_address if server else "0.0.0.0"
        ss_url = generate_ss_url(key.ss_method, key.ss_password, host, key.ss_port, tag)
        responses.append(
            AccessKeyResponse(
                id=key.id,
                server_id=key.server_id,
                ss_port=key.ss_port,
                ss_method=key.ss_method,
                ss_url=ss_url,
                qr_code=generate_qr_base64(ss_url),
                traffic_up=key.traffic_up,
                traffic_down=key.traffic_down,
                is_active=key.is_active,
                created_at=key.created_at,
                server_name=server.name if server else None,
                server_country=server.country if server else None,
            )
        )
    return responses


@router.get("/{key_id}", response_model=AccessKeyResponse)
async def get_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(AccessKey).where(AccessKey.id == key_id, AccessKey.user_id == user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    server = key.server
    tag = f"{server.country}-{server.name}" if server else "VPN"
    host = server.ip_address if server else "0.0.0.0"
    ss_url = generate_ss_url(key.ss_method, key.ss_password, host, key.ss_port, tag)

    return AccessKeyResponse(
        id=key.id,
        server_id=key.server_id,
        ss_port=key.ss_port,
        ss_method=key.ss_method,
        ss_url=ss_url,
        qr_code=generate_qr_base64(ss_url),
        traffic_up=key.traffic_up,
        traffic_down=key.traffic_down,
        is_active=key.is_active,
        created_at=key.created_at,
        server_name=server.name if server else None,
        server_country=server.country if server else None,
    )

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(AccessKey).where(AccessKey.id == key_id, AccessKey.user_id == user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    backend = get_backend(key.server)
    await backend.stop_instance(key.ss_port)
    key.is_active = False
    await db.commit()

@router.post("/{key_id}/regenerate", response_model=AccessKeyResponse)
async def regenerate_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(AccessKey).where(AccessKey.id == key_id, AccessKey.user_id == user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    # Stop old instance
    backend = get_backend(key.server)
    await backend.stop_instance(key.ss_port)

    # Generate new password and restart
    new_password = ss_manager.generate_password()
    key.ss_password = new_password
    await backend.start_instance(key.ss_port, new_password, key.ss_method)
    await db.commit()
    await db.refresh(key)

    server = key.server
    tag = f"{server.country}-{server.name}" if server else "VPN"
    host = server.ip_address if server else "0.0.0.0"
    ss_url = generate_ss_url(key.ss_method, new_password, host, key.ss_port, tag)

    return AccessKeyResponse(
        id=key.id,
        server_id=key.server_id,
        ss_port=key.ss_port,
        ss_method=key.ss_method,
        ss_url=ss_url,
        qr_code=generate_qr_base64(ss_url),
        traffic_up=key.traffic_up,
        traffic_down=key.traffic_down,
        is_active=key.is_active,
        created_at=key.created_at,
        server_name=server.name if server else None,
        server_country=server.country if server else None,
    )
