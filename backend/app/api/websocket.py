import json
import uuid

import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.access_key import AccessKey

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws/speed/{key_id}")
async def speed_websocket(websocket: WebSocket, key_id: uuid.UUID):
    await websocket.accept()

    # Look up the port for this key
    async with async_session() as db:
        result = await db.execute(select(AccessKey).where(AccessKey.id == key_id))
        key = result.scalar_one_or_none()
        if not key:
            await websocket.close(code=4004, reason="Key not found")
            return
        target_port = key.ss_port

    r = redis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("speed_updates")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])
            port_str = str(target_port)
            if target_port in data:
                port_data = data[target_port]
            elif port_str in data:
                port_data = data[port_str]
            else:
                continue

            await websocket.send_json({
                "timestamp": port_data["timestamp"],
                "upload_speed_mbps": port_data["upload_speed_mbps"],
                "download_speed_mbps": port_data["download_speed_mbps"],
                "upload_total_gb": round(port_data.get("upload_total", 0) / 1_073_741_824, 3),
                "download_total_gb": round(port_data.get("download_total", 0) / 1_073_741_824, 3),
            })
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe("speed_updates")
        await pubsub.close()
        await r.close()
