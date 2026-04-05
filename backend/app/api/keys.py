import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.functions import func
from datetime import datetime, timezone

from app.api.deps import get_current_active_user
from app.database import get_db
from app.keys.dependencies import get_key_service
from app.keys.service import AccessKeyService, KeyLimitExceededError, InstanceStartError
from app.models import AccessKey
from app.models.user import PlanType, User
from app.models.server import Server
from app.schemas.access_key import AccessKeyCreate, AccessKeyResponse
from app.servers.dependencies import get_server_service
from app.servers.service import ServerService, ServerNotFoundError
from app.services.shadowsocks import ss_manager
from app.services.server_backend import RemoteAgentBackend
from app.utils.ss import generate_ss_url, generate_qr_base64

router = APIRouter(prefix="/api/keys", tags=["keys"])

PLAN_KEY_LIMITS = {
    PlanType.free: 1,
    PlanType.basic: 3,
    PlanType.pro: 10,
}

@router.post("/create", response_model=AccessKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    data: AccessKeyCreate,
    key_service: AccessKeyService = Depends(get_key_service),
    server_service: ServerService = Depends(get_server_service),
    user: User = Depends(get_current_active_user),
):

    try:
        server = await server_service.get_active(data.server_id)
    except ServerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found or inactive")

    try:
        key, ss_url, qr_code = await key_service.create_key(user, server)
    except KeyLimitExceededError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Key limit reached for your plan")
    except InstanceStartError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start VPN instance")





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

    backend = RemoteAgentBackend.from_server(key.server)
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
    backend = RemoteAgentBackend.from_server(key.server)
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


