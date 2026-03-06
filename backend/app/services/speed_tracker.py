import asyncio
import json
import logging
import time

import redis.asyncio as redis

from app.config import settings
from app.services.shadowsocks import ss_manager

logger = logging.getLogger(__name__)


class SpeedTracker:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._previous: dict[int, dict[str, int]] = {}
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL)
        return self._redis

    def start(self, interval: float = 1.0):
        self._running = True
        self._task = asyncio.create_task(self._run(interval))

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run(self, interval: float):
        while self._running:
            try:
                await self._measure_speed()
            except Exception as e:
                logger.error(f"SpeedTracker error: {e}")
            await asyncio.sleep(interval)

    async def _measure_speed(self):
        current = await ss_manager.get_all_traffic()
        now = time.time()
        r = await self._get_redis()

        speed_data = {}

        for port, traffic in current.items():
            prev = self._previous.get(port, {"upload": 0, "download": 0})

            upload_speed = max(0, traffic["upload"] - prev["upload"])
            download_speed = max(0, traffic["download"] - prev["download"])

            speed_data[port] = {
                "timestamp": now,
                "port": port,
                "upload_speed": upload_speed,
                "download_speed": download_speed,
                "upload_speed_mbps": round(upload_speed * 8 / 1_000_000, 2),
                "download_speed_mbps": round(download_speed * 8 / 1_000_000, 2),
                "upload_total": traffic["upload"],
                "download_total": traffic["download"],
            }

        self._previous = current

        if speed_data:
            await r.publish("speed_updates", json.dumps(speed_data))
            await r.set("latest_speed", json.dumps(speed_data), ex=10)


speed_tracker = SpeedTracker()
