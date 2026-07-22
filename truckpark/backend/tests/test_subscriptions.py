import asyncio
import types
import uuid

from fastapi import HTTPException

from app.models.user import UserRole


def _user(role=UserRole.admin, is_root=True, tenant_id=None):
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        role=role,
        is_root=is_root,
        tenant_id=tenant_id,
    )


def test_slug_base_normalizes_parking_name():
    from app.routers.subscriptions import _slug_base

    assert _slug_base("Jason's Truck Parking, Coimbatore!") == "jason-s-truck-parking-coimbatore"
    assert _slug_base("   ") == "tenant"
    assert len(_slug_base("A" * 100)) == 60


def test_require_platform_admin_allows_only_root_without_tenant():
    async def run():
        from app.core.dependencies import require_platform_admin

        current = _user()
        assert await require_platform_admin(current) is current

    asyncio.run(run())


def test_require_platform_admin_rejects_tenant_owner():
    async def run():
        from app.core.dependencies import require_platform_admin

        try:
            await require_platform_admin(_user(tenant_id=uuid.uuid4()))
        except HTTPException as exc:
            assert exc.status_code == 403
            return
        raise AssertionError("Expected tenant owner to be rejected")

    asyncio.run(run())

