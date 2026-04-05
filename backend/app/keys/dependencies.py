from fastapi import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.database import get_db
from app.keys.repository import AccessKeyRepository
from app.keys.service import AccessKeyService
from app.servers.repository import ServerRepository


def get_key_repository(db: AsyncSession = Depends(get_db)) -> AccessKeyRepository:
    return AccessKeyRepository(db)


def get_key_service(
        repo: AccessKeyRepository = Depends(get_key_repository),
) -> AccessKeyService:
    return AccessKeyService(repo)