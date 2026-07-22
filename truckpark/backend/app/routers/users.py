import secrets
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    PasswordResetRequest,
    PasswordResetResponse,
    UserCreate,
    UserOut,
    UserStatusUpdate,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])


def _is_platform_admin(user: User) -> bool:
    return (
        getattr(user, "role", None) == UserRole.admin
        and bool(getattr(user, "is_root", False))
        and getattr(user, "tenant_id", None) is None
    )


def _ensure_same_tenant(target: User, current_user: User) -> None:
    if _is_platform_admin(current_user):
        return
    if getattr(target, "tenant_id", None) != getattr(current_user, "tenant_id", None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


def _generate_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin)):
    query = select(User).order_by(User.created_at.desc())
    if not _is_platform_admin(current_user):
        query = query.where(User.tenant_id == current_user.tenant_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = await db.execute(select(User).where(User.mobile == payload.mobile))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mobile number already registered")

    user = User(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        mobile=payload.mobile.strip(),
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_root=False,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mobile number or email already registered",
        ) from exc
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_same_tenant(user, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip()
        setattr(user, field, value)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mobile number or email already registered",
        ) from exc
    await db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=UserOut)
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_same_tenant(user, current_user)
    if user.id == current_user.id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable your own account")

    user.is_active = payload.is_active
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_same_tenant(user, current_user)

    temp_password = _generate_temp_password()
    user.password_hash = hash_password(temp_password)
    user.must_reset_password = True
    await db.flush()

    return PasswordResetResponse(
        message="Password reset successfully. Share the temporary password securely with the user.",
        temporary_password=temp_password,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_same_tenant(user, current_user)
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    await db.delete(user)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
