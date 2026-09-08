from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str

    resend_api_key: str = ""
    resend_from_email: str = "Hunger Birds <onboarding@resend.dev>"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    allowed_email_domain: str = "bitmesra.ac.in"
    otp_debug_echo: bool = False

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_upload_folder: str = "hunger_birds"

    cors_origins: str = "*"

    @field_validator("database_url")
    @classmethod
    def use_async_driver(cls, value: str) -> str:
        """Railway (and most hosts) inject a plain postgres:// URL, but the
        async engine needs the asyncpg driver spelled out."""
        for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
            if value.startswith(prefix):
                return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
