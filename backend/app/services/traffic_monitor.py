import asyncio
import logging

from sqlalchemy import select

from app.database import async_session
from app.models.access_key import AccessKey
from app.models.traffic_log import TrafficLog
from app.models.user import User
from app.models.server import Server
from app.services.server_backend import get_backend

logger = logging.getLogger(__name__)


class TrafficMonitor:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self, interval: int = 60):
        self._running = True
        self._task = asyncio.create_task(self._run(interval))

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run(self, interval: int):
        while self._running:
            try:
                await self._collect_traffic()
                await self._check_limits()
            except Exception as e:
                logger.error(f"TrafficMonitor error: {e}")
            await asyncio.sleep(interval)

    async def _collect_traffic(self):
        async with async_session() as db:
            result = await db.execute(select(Server).where(Server.is_active == True))  # noqa: E712
            servers = result.scalars().all()

            for server in servers:
                backend = get_backend(server)
                try:
                    all_traffic = await backend.get_all_traffic()
                except Exception as e:
                    logger.error(f"Failed to get traffic from server {server.name}: {e}")
                    continue

                for port, traffic in all_traffic.items():
                    result = await db.execute(
                        select(AccessKey).where(AccessKey.ss_port == port, AccessKey.is_active == True)  # noqa: E712
                    )
                    key = result.scalar_one_or_none()
                    if not key:
                        continue

                    new_up = traffic["upload"]
                    new_down = traffic["download"]

                    delta_up = max(0, new_up - key.traffic_up) if key.traffic_up > 0 else 0
                    delta_down = max(0, new_down - key.traffic_down) if key.traffic_down > 0 else 0

                    key.traffic_up = new_up
                    key.traffic_down = new_down

                    if delta_up > 0 or delta_down > 0:
                        log = TrafficLog(
                            access_key_id=key.id,
                            bytes_up=delta_up,
                            bytes_down=delta_down,
                        )
                        db.add(log)

                        result = await db.execute(select(User).where(User.id == key.user_id))
                        user = result.scalar_one_or_none()
                        if user:
                            user.traffic_used += delta_up + delta_down

            await db.commit()

    async def _check_limits(self):
        async with async_session() as db:
            result = await db.execute(select(User).where(User.is_active == True))  # noqa: E712
            users = result.scalars().all()

            for user in users:
                if user.traffic_used >= user.traffic_limit:
                    logger.warning(f"User {user.email} exceeded traffic limit ({user.traffic_used}/{user.traffic_limit})")
                    result = await db.execute(
                        select(AccessKey).where(
                            AccessKey.user_id == user.id, AccessKey.is_active == True  # noqa: E712
                        )
                    )
                    keys = result.scalars().all()
                    for key in keys:
                        await get_backend(key.server).stop_instance(key.ss_port)
                        key.is_active = False
                        logger.info(f"Stopped key {key.id} for user {user.email} (traffic limit)")

            await db.commit()


traffic_monitor = TrafficMonitor()
