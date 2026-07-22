"""
Reusable FastAPI dependencies for authentication and role-based access
control. Every protected router imports `require_admin` or
`require_gatekeeper_or_admin` from here rather than re-implementing
auth checks, keeping authorization logic centralized and auditable.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import JWTError, decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def require_root_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin or not current_user.is_root:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Root admin access required")
    return current_user


async def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin or not current_user.is_root or current_user.tenant_id is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin access required")
    return current_user


async def require_gatekeeper_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.admin, UserRole.gatekeeper):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return current_user


def is_platform_admin(user: User) -> bool:
    return user.role == UserRole.admin and user.is_root and user.tenant_id is None


def tenant_filter(model, current_user: User):
    tenant_column = getattr(model, "tenant_id")
    if is_platform_admin(current_user):
        return None
    return tenant_column == current_user.tenant_id


def require_same_tenant(model_obj, current_user: User) -> None:
    if is_platform_admin(current_user):
        return
    if getattr(model_obj, "tenant_id", None) != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
