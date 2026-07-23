"""
Async SQLAlchemy engine + session management.

`get_db` is the FastAPI dependency used by routers to obtain a scoped
AsyncSession per request, with automatic commit/rollback handling.
"""
from collections.abc import AsyncGenerator
import ssl
from urllib.parse import parse_qs, urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


# Build connect_args safely for asyncpg. Do NOT pass libpq-style
# `sslmode` as a connect kwarg (asyncpg.connect doesn't accept it).
connect_args = {}
qs = parse_qs(urlparse(settings.DATABASE_URL).query)
sslmode = qs.get("sslmode", [None])[0]
if sslmode and sslmode.lower() != "disable":
    ctx = ssl.create_default_context()
    connect_args["ssl"] = ctx

# SQLAlchemy/asyncpg support a prepared statement cache size DBAPI arg.
# Use the dialect-supported name so it gets forwarded correctly.
if settings.DB_STATEMENT_CACHE_SIZE:
    connect_args["prepared_statement_cache_size"] = settings.DB_STATEMENT_CACHE_SIZE

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
