import asyncio
import uuid
import types

from fastapi import HTTPException


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeAsyncSession:
    def __init__(self, user):
        self._user = user
        self.deleted = None

    async def execute(self, stmt):
        return FakeResult(self._user)

    async def delete(self, user):
        self.deleted = user

    async def flush(self):
        return None

    async def refresh(self, user):
        return None


def _make_user(is_root=False, id=None):
    return types.SimpleNamespace(is_root=is_root, id=id or uuid.uuid4())


def test_delete_user_not_found():
    async def run():
        from app.routers import users

        fake_db = FakeAsyncSession(None)
        current = _make_user(is_root=False)
        try:
            await users.delete_user(uuid.uuid4(), db=fake_db, current_user=current)
        except HTTPException as exc:
            assert exc.status_code == 404
            return
        raise AssertionError("Expected HTTPException for not found")

    asyncio.run(run())


def test_delete_user_root_forbidden():
    async def run():
        from app.routers import users
        from fastapi import Response

        user = _make_user(is_root=True)
        fake_db = FakeAsyncSession(user)
        current = _make_user(is_root=False)
        res = await users.delete_user(user.id, db=fake_db, current_user=current)
        assert isinstance(res, Response)
        assert res.status_code == 204
        assert fake_db.deleted is user

    asyncio.run(run())


def test_delete_user_cannot_delete_self():
    async def run():
        from app.routers import users

        user = _make_user(is_root=False)
        fake_db = FakeAsyncSession(user)
        current = user
        try:
            await users.delete_user(user.id, db=fake_db, current_user=current)
        except HTTPException as exc:
            assert exc.status_code == 400
            return
        raise AssertionError("Expected HTTPException for deleting self")

    asyncio.run(run())


def test_delete_user_success():
    async def run():
        from app.routers import users
        from fastapi import Response

        user = _make_user(is_root=False)
        fake_db = FakeAsyncSession(user)
        current = _make_user(is_root=False)

        res = await users.delete_user(user.id, db=fake_db, current_user=current)
        # router returns a Response with 204
        assert isinstance(res, Response)
        assert res.status_code == 204
        assert fake_db.deleted is user

    asyncio.run(run())


def test_update_user_status_allows_root_user():
    async def run():
        from app.routers import users
        from app.schemas.auth import UserStatusUpdate

        user = _make_user(is_root=True)
        user.is_active = True
        fake_db = FakeAsyncSession(user)
        current = _make_user(is_root=False)

        res = await users.update_user_status(
            user.id,
            UserStatusUpdate(is_active=False),
            db=fake_db,
            current_user=current,
        )

        assert res is user
        assert user.is_active is False

    asyncio.run(run())


def test_update_user_status_cannot_disable_self():
    async def run():
        from app.routers import users
        from app.schemas.auth import UserStatusUpdate

        user = _make_user(is_root=True)
        user.is_active = True
        fake_db = FakeAsyncSession(user)

        try:
            await users.update_user_status(
                user.id,
                UserStatusUpdate(is_active=False),
                db=fake_db,
                current_user=user,
            )
        except HTTPException as exc:
            assert exc.status_code == 400
            return
        raise AssertionError("Expected HTTPException for disabling self")

    asyncio.run(run())
