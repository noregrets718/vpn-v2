import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session
from app.services.shadowsocks import ss_manager
from app.models.user import User
from app.utils.crypto import hash_password
from sqlalchemy import select
from prometheus_fastapi_instrumentator import Instrumentator
from app.services.health_checker import health_checker

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def create_default_admin():
    admin_email = settings.ADMIN_EMAIL
    admin_password = settings.ADMIN_PASSWORD
    if not admin_email or not admin_password:
        return
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == admin_email))
        if result.scalar_one_or_none():
            return  # уже существует
        user = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            is_admin=True,
        )
        db.add(user)
        await db.commit()
        logger.info(f"Created admin user: {admin_email}")


async def ensure_local_server():
    from app.models.server import Server
    from sqlalchemy import select
    import httpx

    async with async_session() as db:
        result = await db.execute(select(Server).where(Server.is_local == True))  # noqa: E712
        if result.scalar_one_or_none():
            return

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get("https://api.ipify.org?format=json")
                public_ip = r.json()["ip"]
        except Exception:
            public_ip = "127.0.0.1"

        server = Server(
            name=settings.LOCAL_SERVER_NAME,
            ip_address=public_ip,
            country=settings.LOCAL_SERVER_COUNTRY,
            is_local=True,
        )
        db.add(server)
        await db.commit()
        logger.info(f"Registered local server with IP {public_ip}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting VPN service...")
    await create_default_admin()
    await ensure_local_server()
    async with async_session() as db:
        restored = await ss_manager.restore_instances(db)
        logger.info(f"Restored {restored} SS instances")

    # Import here to avoid circular imports
    from app.services.traffic_monitor import traffic_monitor
    from app.services.speed_tracker import speed_tracker

    traffic_monitor.start()
    speed_tracker.start()
    health_checker.start()
    logger.info("Background services started")

    yield

    # Shutdown
    logger.info("Shutting down VPN service...")
    traffic_monitor.stop()
    speed_tracker.stop()
    health_checker.stop()
    await ss_manager.shutdown()
    logger.info("VPN service stopped")


app = FastAPI(title="VPN Service", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.api.auth import router as auth_router
from app.api.servers import router as servers_router
from app.api.keys import router as keys_router
from app.api.traffic import router as traffic_router
from app.api.websocket import router as ws_router
from app.api.admin import router as admin_router


app.include_router(auth_router)
app.include_router(servers_router)
app.include_router(keys_router)
app.include_router(traffic_router)
app.include_router(ws_router)
app.include_router(admin_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
