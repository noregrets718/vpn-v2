

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.servers.repository import ServerRepository
from app.servers.service import ServerService, ServerNotFoundError
import uuid


def get_server_repository(db: AsyncSession = Depends(get_db)) -> ServerRepository:
    return ServerRepository(db)


def get_server_service(
        repo: ServerRepository = Depends(get_server_repository),
) -> ServerService:
    return ServerService(repo)