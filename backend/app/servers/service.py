import uuid

from app.core.service import BaseService
from app.models.server import Server
from app.servers.repository import ServerRepository


class ServerNotFoundError(Exception):
    pass

class ServerService(BaseService[ServerRepository]):

    async def get_active(self, server_id: uuid.UUID) -> Server:
        server = await self.repo.get_active_by_id(server_id)
        if not server:
            raise ServerNotFoundError()
        return server

    async def list_active(self) -> list[Server]:
        return await self.repo.get_all_active()