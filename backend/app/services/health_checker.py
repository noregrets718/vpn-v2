import asyncio
import logging

import redis.asyncio as redis

from app.config import settings
from app.database import async_session
from app.models.access_key import AccessKey
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def _tcp_check(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        return True
    except Exception:
        return False

class InstanceHealthChecker:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._redis: redis.Redis | None = None

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL)
        return self._redis

    def start(self, interval: float = 300.0):
        self._running = True
        self._task = asyncio.create_task(self._run(interval))

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()


    async def _run(self, interval: float):
        while self._running:
            try:
                await self._check_all()
            except Exception as e:
                logger.error(f"HealthChecker error: {e}")
            await asyncio.sleep(interval)

    async def _check_all(self):
        async with async_session() as db:
            result = await db.execute(
                select(AccessKey).where(AccessKey.is_active == True)  # noqa: E712
            )
            keys = result.scalars().all()

        r = self._get_redis()

        async def check_one(key: AccessKey):
            host = key.server.ip_address if key.server else None
            if not host:
                return
            alive = await _tcp_check(host, key.ss_port)
            await r.set(f"instance_alive:{key.id}", "1" if alive else "0", ex=600)
            if not alive:
                await self._notify(key)

        await asyncio.gather(*[check_one(k) for k in keys])
        logger.info(f"HealthChecker: checked {len(keys)} instances")

    async def _notify(self, key: AccessKey):
        # TODO: send Telegram notification
        logger.warning(
            f"Instance {key.id} port {key.ss_port} on server "
            f"{key.server.name if key.server else '?'} is not responding"
        )

health_checker = InstanceHealthChecker()