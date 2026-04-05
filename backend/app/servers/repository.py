import uuid

from app.core.repository import BaseRepository
from sqlalchemy import select

from app.models import Server


class ServerRepository(BaseRepository):
    async def get_active_by_id(self, server_id: uuid.UUID) -> Server | None:
        result = await self.db.execute(
            select(Server).where(Server.id == server_id, Server.is_active == True)
            # noqa: E712
        )
        return result.scalar_one_or_none()

    async def get_all_active(self) -> list[Server]:
        result = await self.db.execute(
            select(Server).where(Server.is_active == True).order_by(Server.name)  # noqa: E712
        )
        return list(result.scalars().all())

