"""
Seed script. Run once after migrations to bootstrap:
  - the root admin account (owner)
  - default billing rules matching the spec example
  - a default system_settings row

Usage:
    python -m app.db.seed
"""
import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.billing_rule import BillingRule
from app.models.system_settings import SystemSettings
from app.models.user import User, UserRole
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_RULES = [
    {"rule_name": "First 12 Hours", "from_hours": 0, "to_hours": 12, "charge": 100, "priority": 1},
    {"rule_name": "12-24 Hours", "from_hours": 12, "to_hours": 24, "charge": 150, "priority": 2},
    {"rule_name": "Additional Day", "from_hours": 24, "to_hours": None, "charge": 100, "priority": 3},
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # Root admin. Keep local/demo credentials deterministic so the
        # launcher can recreate a usable system without wiping volumes.
        result = await db.execute(select(User).where(User.mobile == settings.ROOT_ADMIN_MOBILE))
        root = result.scalar_one_or_none()
        if root is None:
            root = User(
                name=settings.ROOT_ADMIN_NAME,
                mobile=settings.ROOT_ADMIN_MOBILE,
                password_hash=hash_password(settings.ROOT_ADMIN_PASSWORD),
                role=UserRole.admin,
                is_active=True,
                is_root=True,
            )
            db.add(root)
            logger.info("Created root admin: %s", settings.ROOT_ADMIN_MOBILE)
        else:
            root.name = settings.ROOT_ADMIN_NAME
            root.password_hash = hash_password(settings.ROOT_ADMIN_PASSWORD)
            root.role = UserRole.admin
            root.is_active = True
            root.is_root = True
            logger.info("Updated root admin credentials: %s", settings.ROOT_ADMIN_MOBILE)

        # Default gatekeeper
        result = await db.execute(select(User).where(User.mobile == settings.GATEKEEPER_MOBILE))
        gatekeeper = result.scalar_one_or_none()
        if gatekeeper is None:
            gatekeeper = User(
                name=settings.GATEKEEPER_NAME,
                mobile=settings.GATEKEEPER_MOBILE,
                password_hash=hash_password(settings.GATEKEEPER_PASSWORD),
                role=UserRole.gatekeeper,
                is_active=True,
                is_root=False,
            )
            db.add(gatekeeper)
            logger.info("Created default gatekeeper: %s", settings.GATEKEEPER_MOBILE)
        else:
            gatekeeper.name = settings.GATEKEEPER_NAME
            gatekeeper.password_hash = hash_password(settings.GATEKEEPER_PASSWORD)
            gatekeeper.role = UserRole.gatekeeper
            gatekeeper.is_active = True
            gatekeeper.is_root = False
            logger.info("Updated default gatekeeper credentials: %s", settings.GATEKEEPER_MOBILE)

        # Default billing rules
        existing_rules = (await db.execute(select(BillingRule))).scalars().first()
        if existing_rules is None:
            for rule in DEFAULT_RULES:
                db.add(BillingRule(**rule))
            logger.info("Seeded %d default billing rules", len(DEFAULT_RULES))
        else:
            logger.info("Billing rules already exist, skipping")

        # Default system settings row
        existing_settings = (await db.execute(select(SystemSettings))).scalar_one_or_none()
        if existing_settings is None:
            db.add(SystemSettings(parking_name="My Truck Yard", notifications_enabled=True))
            logger.info("Created default system settings row")

        await db.commit()
    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
