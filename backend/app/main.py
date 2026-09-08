from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.media.router import router as media_router
from app.modules.menu.router import router as menu_router
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
