import secrets
import uuid
from datetime import datetime, timezone

from app.core.service import BaseService
from app.keys.repository import AccessKeyRepository
from app.config import settings
from app.models import AccessKey, Server, User
from app.services.server_backend import RemoteAgentBackend
from app.utils.ss import generate_ss_url, generate_qr_base64


class NoFreePortsError(Exception):
    pass
class KeyLimitExceededError(Exception):
    pass


class InstanceStartError(Exception):
    pass


class KeyNotFoundError(Exception):
    pass


class AccessKeyService(BaseService[AccessKeyRepository]):


    def _generate_password(self, length: int = 32) -> str:
        return secrets.token_urlsafe(length)

    async def _get_next_free_port(self, server_id: uuid.UUID) -> int:
        last_used_port = await self.repo.get_last_used_port(server_id)

        if last_used_port is None:
            return settings.PORT_RANGE_START

        next_port = last_used_port + 1
        if next_port <= settings.PORT_RANGE_END:
            return next_port

        raise NoFreePortsError()

    def _build_response_urls(self, key: AccessKey, server: Server) -> tuple[str, str]:
        tag = f"{server.country}-{server.name}"
        ss_url = generate_ss_url(key.ss_method, key.ss_password, server.ip_address, key.ss_port, tag)
        qr_code = generate_qr_base64(ss_url)
        return ss_url, qr_code

    async def create_key(self, user: User, server: Server) -> tuple[AccessKey,str, str]:
        limit = settings.PLAN_LIMIT_FREE
        active_count = await self.repo.count_active(user.id)
        if active_count >= limit:
            raise KeyLimitExceededError
        port = await self._get_next_free_port(server.id)
        password = self._generate_password()
        backend = RemoteAgentBackend.from_server(server)
        if not await backend.start_instance(port, password, settings.SS_METHOD):
            raise InstanceStartError()

        key = AccessKey(
            user_id=user.id,
            server_id=server.id,
            ss_port=port,
            ss_password=password,
            ss_method=settings.SS_METHOD,
            started_at=datetime.now(timezone.utc),
        )

        await self.repo.save(key)
        await self.repo.db.commit()

        ss_url, qr_code = self._build_response_urls(key, server)
        return key, ss_url, qr_code


    async def list_active_by_user(self, user_id: uuid.UUID) -> list[AccessKey]:
        return await self.repo.get_active_by_user(user_id)

    async def get(self, key_id: uuid.UUID, user_id: uuid.UUID) -> AccessKey:
        key = await self.repo.get_by_id(key_id, user_id)
        if not key:
            raise KeyNotFoundError()
        return key

    async def delete(self, key_id: uuid.UUID, user_id: uuid.UUID) -> None:
        key = await self.repo.get_by_id(key_id, user_id)
        if not key:
            raise KeyNotFoundError()
        backend = RemoteAgentBackend.from_server(key.server)
        await backend.stop_instance(key.ss_port)
        key.is_active = False
        key.started_at = None
        await self.repo.db.commit()

    async def regenerate(self, key_id: uuid.UUID, user_id: uuid.UUID) -> AccessKey:
        key = await self.repo.get_by_id(key_id, user_id)
        if not key:
            raise KeyNotFoundError()
        backend = RemoteAgentBackend.from_server(key.server)
        await backend.stop_instance(key.ss_port)
        new_password = self._generate_password()
        key.ss_password = new_password
        await backend.start_instance(key.ss_port, new_password, key.ss_method)
        await self.repo.db.commit()
        await self.repo.db.refresh(key)
        return key








