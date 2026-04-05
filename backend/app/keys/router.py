import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_user
from app.keys.dependencies import get_key_service
from app.keys.service import AccessKeyService, KeyLimitExceededError, InstanceStartError, KeyNotFoundError
from app.models import User
from app.schemas.access_key import AccessKeyResponse, AccessKeyCreate
from app.servers.dependencies import get_server_service
from app.servers.service import ServerService, ServerNotFoundError
from app.utils.ss import generate_ss_url, generate_qr_base64

router = APIRouter(prefix="/api/keys", tags=["keys"])

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
  user: User = Depends(get_current_active_user),
  key_service: AccessKeyService = Depends(get_key_service),
):
  keys = await key_service.list_active_by_user(user.id)
  responses = []
  for key in keys:
      server = key.server
      tag = f"{server.country}-{server.name}" if server else "VPN"
      host = server.ip_address if server else "0.0.0.0"
      ss_url = generate_ss_url(key.ss_method, key.ss_password, host, key.ss_port, tag)
      responses.append(AccessKeyResponse(
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
      ))
  return responses

@router.get("/{key_id}", response_model=AccessKeyResponse)
async def get_key(
  key_id: uuid.UUID,
  user: User = Depends(get_current_active_user),
  key_service: AccessKeyService = Depends(get_key_service),
):
  try:
      key = await key_service.get(key_id, user.id)
  except KeyNotFoundError:
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
  user: User = Depends(get_current_active_user),
  service: AccessKeyService = Depends(get_key_service),
):
  try:
      await service.delete(key_id, user.id)
  except KeyNotFoundError:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

@router.post("/{key_id}/regenerate", response_model=AccessKeyResponse)
async def regenerate_key(
  key_id: uuid.UUID,
  user: User = Depends(get_current_active_user),
  key_service: AccessKeyService = Depends(get_key_service),
):
  try:
      key, ss_url, qr_code = await key_service.regenerate(key_id, user.id)
  except KeyNotFoundError:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

  server = key.server
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
      server_name=server.name if server else None,
      server_country=server.country if server else None,
  )
