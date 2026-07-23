"""
Application configuration.

All values are sourced from environment variables (see .env.example).
Uses pydantic-settings so config is validated on startup -- the app
will fail fast with a clear error instead of crashing later at runtime.
"""
from functools import lru_cache
from typing import List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import field_validator, model_validator
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
    SECRET_KEY: str = "jshdhsdbsjdeyubxjshdjhsdsjnsjjdjhdjsdjshdjshdjhsd"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/truckpark"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_STATEMENT_CACHE_SIZE: int = 0

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v):
        if not isinstance(v, str):
            return v

        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]

        # Remove libpq-style `sslmode` from the URL query so the SQLAlchemy
        # asyncpg dialect does not forward it as a keyword arg to asyncpg.connect
        # (asyncpg.connect doesn't accept an `sslmode` kwarg). Keep other
        # query params intact.
        try:
            parsed = urlparse(v)
            if parsed.query:
                qs = [(k, val) for k, val in parse_qsl(parsed.query) if k.lower() != "sslmode"]
                new_query = urlencode(qs)
                if new_query != parsed.query:
                    parsed = parsed._replace(query=new_query)
                    return urlunparse(parsed)
        except Exception:
            # If anything goes wrong, fall back to returning original value.
            return v

        return v

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ORIGIN_REGEX: Optional[str] = None

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

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.APP_ENV == "production":
            if self.SECRET_KEY == "CHANGE_ME_IN_PRODUCTION" or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if self.ROOT_ADMIN_PASSWORD in {"0000", "ChangeMe123!"} or len(self.ROOT_ADMIN_PASSWORD) < 8:
                raise ValueError("ROOT_ADMIN_PASSWORD must be changed in production")
            if self.GATEKEEPER_PASSWORD == "0000" or len(self.GATEKEEPER_PASSWORD) < 6:
                raise ValueError("GATEKEEPER_PASSWORD must be changed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
