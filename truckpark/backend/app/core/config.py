"""
Application configuration.

All values are sourced from environment variables (see .env.example).
Uses pydantic-settings so config is validated on startup -- the app
will fail fast with a clear error instead of crashing later at runtime.
"""
from functools import lru_cache
from typing import List

from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "Smart Truck Parking Management System"
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            value = v.strip().lower()
            if value in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if value in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True
        return v

    # --- Security / JWT ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/truckpark"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # --- MSG91 (defaults are blank; real values come from SystemSettings in DB
    # or env. Env values act as a fallback/bootstrap.) ---
    MSG91_AUTHKEY: str = ""
    MSG91_SENDER_ID: str = ""
    MSG91_WHATSAPP_NUMBER: str = ""
    MSG91_BASE_URL: str = "https://control.msg91.com/api/v5"
    MSG91_ENTRY_TEMPLATE_NAME: str = "truck_entry_notification"
    MSG91_EXIT_TEMPLATE_NAME: str = "truck_exit_receipt"
    MSG91_NAMESPACE: str = ""

    # --- File storage (entry/exit photos) ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 5

    # --- Pagination ---
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # --- Timezone ---
    DISPLAY_TIMEZONE: str = "Asia/Kolkata"

    # --- Root admin bootstrap (used by seed script only) ---
    ROOT_ADMIN_NAME: str = "Owner"
    ROOT_ADMIN_MOBILE: str = "9999999999"
    ROOT_ADMIN_PASSWORD: str = "ChangeMe123!"

    # --- Default gatekeeper bootstrap (used by seed script only) ---
    GATEKEEPER_NAME: str = "Gatekeeper"
    GATEKEEPER_MOBILE: str = "8888888888"
    GATEKEEPER_PASSWORD: str = "0000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
