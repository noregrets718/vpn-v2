import logging
import uuid
import httpx

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy import select

from app.api.deps import get_admin_user
from app.database import get_db
from app.models import Server, User
from app.schemas.server import ServerResponse, ServerCreate, ServerUpdate
from app.services.server_backend import RemoteAgentBackend

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
router = APIRouter(prefix="/api/servers", tags=["servers"])

@router.get("", response_model=list[ServerResponse])
async def list_servers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Server).where(Server.is_active == True).order_by(Server.name))  # noqa: E712
    return result.scalars().all()

@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(server_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return server

@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
        request: Request,
        data: ServerCreate,
        db: AsyncSession = Depends(get_db),
        admin: User = Depends(get_admin_user),
):
    body = await request.json()
    logger.info(f"request body: {body}")
    fields = data.model_dump()

    if not data.is_local and data.agent_url and data.agent_token:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{data.agent_url.rstrip('/')}/info",
                    headers={"X-Agent-Token": data.agent_token},
                )
                if r.status_code == 200:
                    info = r.json()
                    fields["ip_address"] = info["ip"]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Cannot reach agent: {e}")

    server = Server(**fields)
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server

@router.patch("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: uuid.UUID,
    data: ServerUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(server, field, value)

    await db.commit()
    await db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
  server_id: uuid.UUID,
  db: AsyncSession = Depends(get_db),
  admin: User = Depends(get_admin_user),
):
  result = await db.execute(select(Server).where(Server.id == server_id))
  server = result.scalar_one_or_none()
  if not server:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
  server.is_active = False
  await db.commit()

@router.get("/{server_id}/health")
async def server_health(
  server_id: uuid.UUID,
  db: AsyncSession = Depends(get_db),
  admin: User = Depends(get_admin_user),
):
  result = await db.execute(select(Server).where(Server.id == server_id))
  server = result.scalar_one_or_none()
  if not server:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")


  data = await RemoteAgentBackend.from_server(server).health_check()
  return {"online": data.get("status") == "ok", "active_instances": data.get("active_instances", 0)}

