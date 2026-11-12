from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.account_errors import AccountDataError
from app.core.auth_errors import AuthenticationError
from app.core.config import Settings
from app.main import app
from app.models.favorite import Favorite
from app.models.translation import Translation
from app.models.user import User
from app.models.user_preference import UserPreference
from app.schemas.account import HistoryCreateRequest, ProfileUpdateRequest
from app.services.account import PASSWORD_HASHER, AccountService, HistoryService, ProfileService
from app.services.auth import AuthContext
from app.services.document_jobs import require_document_owner


class FakeAccountDB:
    def __init__(self, preference: UserPreference | None = None) -> None:
        self.preference = preference
        self.added: list[object] = []
        self.commits = 0

    async def get(self, model, _identifier):
        return self.preference if model is UserPreference else None

    def add(self, value) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        now = datetime.now(UTC)
        for value in self.added:
            if isinstance(value, (Translation, Favorite)):
                value.id = value.id or uuid4()
                value.created_at = value.created_at or now

    async def commit(self) -> None:
        self.commits += 1


class FakeDeletionDB(FakeAccountDB):
    async def scalars(self, _query):
        return []

    async def execute(self, _query):
        return type("Result", (), {"rowcount": 1})()


def account_context(user_id=None) -> AuthContext:
    user = User(
        id=user_id or uuid4(),
        email="user@example.com",
        password_hash="not-used",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    return AuthContext(
        user=user,
        session=None,  # type: ignore[arg-type]
        transport="bearer",
    )


@pytest.mark.asyncio
async def test_account_endpoints_require_authentication():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in (
            "/api/v1/profile",
            "/api/v1/preferences",
            "/api/v1/history",
            "/api/v1/favorites",
            "/api/v1/account/export",
        ):
            response = await client.get(path)
            assert response.status_code == 401, (path, response.text)
            assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_history_requires_explicit_privacy_opt_in():
    context = account_context()
    payload = HistoryCreateRequest(
        source_language="en",
        target_language="my",
        source_text="Hello",
        translated_text="မင်္ဂလာပါ",
        provider="azure",
    )
    disabled = FakeAccountDB(UserPreference(user_id=context.user.id, history_enabled=False))
    with pytest.raises(AccountDataError) as error:
        await HistoryService(disabled).create(context, payload)
    assert error.value.code == "HISTORY_OPT_IN_REQUIRED"
    assert disabled.added == []

    enabled = FakeAccountDB(UserPreference(user_id=context.user.id, history_enabled=True))
    item = await HistoryService(enabled).create(context, payload)
    assert item.source_text == "Hello"
    assert item.translated_text == "မင်္ဂလာပါ"
    saved = next(value for value in enabled.added if isinstance(value, Translation))
    assert saved.user_id == context.user.id


@pytest.mark.asyncio
async def test_profile_update_does_not_accept_or_change_email():
    context = account_context()
    db = FakeAccountDB()
    response = await ProfileService(db).update(
        context, ProfileUpdateRequest(display_name="  Ko  Min  ")
    )
    assert response.display_name == "Ko Min"
    assert response.email == "user@example.com"
    assert context.user.email == "user@example.com"


@pytest.mark.asyncio
async def test_account_deletion_requires_reauthentication_and_cleans_account(tmp_path):
    context = account_context()
    context.user.password_hash = PASSWORD_HASHER.hash("CorrectHorse9!")
    db = FakeDeletionDB()
    service = AccountService(db, storage_root=str(tmp_path))

    with pytest.raises(AccountDataError) as error:
        await service.delete_account(context, "wrong-password")
    assert error.value.code == "RECENT_REAUTHENTICATION_REQUIRED"
    assert db.commits == 0

    await service.delete_account(context, "CorrectHorse9!")
    assert db.commits == 1


@pytest.mark.asyncio
async def test_invalid_session_cannot_fall_back_to_guest_document_owner(monkeypatch):
    settings = Settings(
        document_jobs_enabled=True,
        document_guest_mode_enabled=True,
        document_guest_capability_token="development-only",
        redis_url="redis://localhost:6379/0",
    )
    monkeypatch.setattr("app.services.document_jobs.get_settings", lambda: settings)

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/documents/job",
            "headers":[
                (b"authorization", b"Bearer invalid-session"),
                (b"x-document-capability-token", b"development-only"),
            ],
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
        }
    )

    class EmptyDB:
        async def scalar(self, _query):
            return None

    with pytest.raises(AuthenticationError):
        await require_document_owner(request, EmptyDB(), "development-only")


def test_phase_6b_migration_adds_profile_and_privacy_fields():
    from pathlib import Path

    migration = Path(__file__).parents[1] / "alembic/versions/0009_profiles_history.py"
    content = migration.read_text()
    assert '"display_name"' in content
    assert '"history_enabled"' in content
    assert "ix_translations_user_languages_created_at" in content
