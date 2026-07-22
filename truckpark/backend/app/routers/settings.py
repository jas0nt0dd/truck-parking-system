from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.schemas.settings import SystemSettingsOut, SystemSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


async def _get_or_create_settings(db: AsyncSession, current_user: User) -> SystemSettings:
    result = await db.execute(select(SystemSettings).where(SystemSettings.tenant_id == current_user.tenant_id).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemSettings(
            tenant_id=current_user.tenant_id,
            parking_name="My Truck Yard",
            notifications_enabled=True,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
    return row


@router.get("", response_model=SystemSettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin)):
    return await _get_or_create_settings(db, current_user)


@router.put("", response_model=SystemSettingsOut)
async def update_settings(
    payload: SystemSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    row = await _get_or_create_settings(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.flush()
    await db.refresh(row)
    return row
