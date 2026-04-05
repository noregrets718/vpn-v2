import uuid

from sqlalchemy import select, func

from app.core.repository import BaseRepository
from app.models import AccessKey


class AccessKeyRepository(BaseRepository):

    async def count_active(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(AccessKey)
            .where(AccessKey.user_id == user_id, AccessKey.is_active == True)  # noqa: E712
        )
        return result.scalar()


    async def get_last_used_port(self, server_id: uuid.UUID) -> int | None:
        result = await self.db.execute(
            select(AccessKey.ss_port)
            .where(AccessKey.server_id == server_id)
            .order_by(AccessKey.ss_port.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_ports(self, server_id: uuid.UUID) -> set[int]:
        result = await self.db.execute(
            select(AccessKey.ss_port)
            .where(AccessKey.server_id == server_id, AccessKey.is_active == True)  # noqa: E712
            .order_by(AccessKey.ss_port)
        )
        return {row[0] for row in result.all()}


    async def get_active_by_user(self, user_id: uuid.UUID) -> list[AccessKey]:
        result = await self.db.execute(
            select(AccessKey)
            .where(AccessKey.user_id == user_id, AccessKey.is_active == True)  # noqa: E712
            .order_by(AccessKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, key_id: uuid.UUID, user_id: uuid.UUID) -> AccessKey | None:
        result = await self.db.execute(
            select(AccessKey).where(AccessKey.id == key_id, AccessKey.user_id == user_id)
        )
        return result.scalar_one_or_none()


    async def save(self, key: AccessKey) -> AccessKey:
        self.db.add(key)
        await self.db.flush()  # записывает в сессию, но не коммитит
        await self.db.refresh(key)
        return key