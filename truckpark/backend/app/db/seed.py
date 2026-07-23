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
from app.core.security import hash_password, verify_password
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
        result = await db.execute(select(User).where(User.is_root.is_(True)))
        roots = result.scalars().all()
        root = roots[0] if roots else None
        if len(roots) > 1:
            logger.warning(
                "Multiple root admin records found; using the first one for env sync."
            )

        if root is None:
            root = User(
                tenant_id=None,
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
            updated = False
            if root.mobile != settings.ROOT_ADMIN_MOBILE:
                root.mobile = settings.ROOT_ADMIN_MOBILE
                updated = True
            if root.name != settings.ROOT_ADMIN_NAME:
                root.name = settings.ROOT_ADMIN_NAME
                updated = True
            if root.role != UserRole.admin:
                root.role = UserRole.admin
                updated = True
            if not root.is_active:
                root.is_active = True
                updated = True
            if not root.is_root:
                root.is_root = True
                updated = True
            if not verify_password(settings.ROOT_ADMIN_PASSWORD, root.password_hash):
                root.password_hash = hash_password(settings.ROOT_ADMIN_PASSWORD)
                updated = True
            if updated:
                logger.info("Updated root admin credentials from env")
            else:
                logger.info("Root admin already exists with current env values")

        # Default gatekeeper
        result = await db.execute(select(User).where(User.mobile == settings.GATEKEEPER_MOBILE))
        gatekeepers = result.scalars().all()
        gatekeeper = gatekeepers[0] if gatekeepers else None
        if len(gatekeepers) > 1:
            logger.warning(
                "Multiple gatekeeper records found for mobile %s; using the first one for env sync.",
                settings.GATEKEEPER_MOBILE,
            )

        if gatekeeper is None:
            gatekeeper = User(
                tenant_id=None,
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
            updated = False
            if gatekeeper.name != settings.GATEKEEPER_NAME:
                gatekeeper.name = settings.GATEKEEPER_NAME
                updated = True
            if gatekeeper.role != UserRole.gatekeeper:
                gatekeeper.role = UserRole.gatekeeper
                updated = True
            if not gatekeeper.is_active:
                gatekeeper.is_active = True
                updated = True
            if gatekeeper.is_root:
                gatekeeper.is_root = False
                updated = True
            if not verify_password(settings.GATEKEEPER_PASSWORD, gatekeeper.password_hash):
                gatekeeper.password_hash = hash_password(settings.GATEKEEPER_PASSWORD)
                updated = True
            if updated:
                logger.info("Updated default gatekeeper credentials from env")
            else:
                logger.info("Default gatekeeper already exists with current env values")

        # Platform-level default billing rules
        existing_rules = (await db.execute(select(BillingRule).where(BillingRule.tenant_id.is_(None)))).scalars().first()
        if existing_rules is None:
            for rule in DEFAULT_RULES:
                db.add(BillingRule(tenant_id=None, **rule))
            logger.info("Seeded %d default billing rules", len(DEFAULT_RULES))
        else:
            logger.info("Billing rules already exist, skipping")

        # Platform-level default system settings row
        existing_settings = (
            await db.execute(select(SystemSettings).where(SystemSettings.tenant_id.is_(None)).limit(1))
        ).scalar_one_or_none()
        if existing_settings is None:
            db.add(SystemSettings(tenant_id=None, parking_name="My Truck Yard", notifications_enabled=True))
            logger.info("Created default system settings row")

        await db.commit()
    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
