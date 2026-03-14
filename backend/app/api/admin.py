import uuid


from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_admin_user
from app.models import User, Server
from app.schemas.server import AdminServerResponse
from app.schemas.user import AdminUserResponse, AdminUserUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db


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



