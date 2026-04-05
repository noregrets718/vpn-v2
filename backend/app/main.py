import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.traffic_monitor import traffic_monitor
from app.services.speed_tracker import speed_tracker
from app.config import settings
from app.database import async_session
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



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting VPN service...")
    await create_default_admin()
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
from app.keys.router import router as keys_router
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
