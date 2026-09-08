from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db.session import get_db
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.media.router import router as media_router
from app.modules.menu.router import router as menu_router
from app.modules.orders.router import router as orders_router
from app.modules.orders.router import vendor_orders_router
from app.modules.realtime.router import router as realtime_router
from app.modules.vendors.router import router as vendors_router

settings = get_settings()

app = FastAPI(title="Hunger Birds API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(vendors_router)
app.include_router(menu_router)
app.include_router(admin_router)
app.include_router(media_router)
app.include_router(orders_router)
app.include_router(vendor_orders_router)
app.include_router(realtime_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    """Fails unless both Postgres and Redis actually answer, so a passing
    deploy healthcheck means the service can really serve traffic."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"database unreachable: {exc}")

    try:
        await redis.ping()
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"redis unreachable: {exc}")

    return {"status": "ready", "database": "ok", "redis": "ok"}
