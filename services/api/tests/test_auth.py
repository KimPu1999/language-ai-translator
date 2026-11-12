from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.auth_errors import AuthenticationError
from app.core.auth_rate_limit import InMemoryAuthRateLimiter
from app.core.config import Settings
from app.main import app
from app.models.auth_action_token import AuthActionToken
from app.models.auth_session import AuthSession
from app.models.user import User
from app.providers.email.base import EmailMessage, EmailProvider
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth import (
    PASSWORD_HASHER,
    AuthService,
    get_auth_context,
    hash_opaque_token,
    normalize_email,
)


class MemoryEmailProvider(EmailProvider):
    messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


class FakeAuthSession:
    def __init__(self, *, scalar_values=None, user=None):
        self.scalar_values = list(scalar_values or [])
        self.user = user
        self.added = []
        self.commits = 0

    async def scalar(self, _query):
        return self.scalar_values.pop(0) if self.scalar_values else None

    async def get(self, model, _identifier):
        return self.user if model is User else None

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        now = datetime.now(UTC)
        for value in self.added:
            if isinstance(value, User):
                value.id = value.id or uuid4()
                value.created_at = value.created_at or now
                value.updated_at = value.updated_at or now
            if isinstance(value, AuthSession):
                value.id = value.id or uuid4()
                value.created_at = value.created_at or now
                value.last_seen_at = value.last_seen_at or now
            if isinstance(value, AuthActionToken):
                value.id = value.id or uuid4()
                value.created_at = value.created_at or now

    async def commit(self):
        self.commits += 1

    async def execute(self, _query):
        return None

    async def scalars(self, _query):
        return []


@pytest.fixture
def auth_settings(tmp_path):
    return Settings(
        database_url="postgresql+asyncpg://localhost:5432/lingua",
        auth_dev_mailbox_dir=str(tmp_path / "mailbox"),
    )


@pytest.mark.asyncio
async def test_registration_hashes_password_and_sends_verification_without_signing_in(
    monkeypatch, auth_settings
):
    session = FakeAuthSession()
    mail = MemoryEmailProvider()
    mail.messages = []
    monkeypatch.setattr("app.services.auth.get_settings", lambda: auth_settings)
    monkeypatch.setattr("app.services.auth.get_email_provider", lambda _settings: mail)
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_settings", lambda: auth_settings)

    async def fake_db():
        yield session

    from app.db.session import get_db

    app.dependency_overrides[get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "User@Example.com",
                    "password": "Correct9!A",
                    "client": "web",
                },
            )
        assert response.status_code == 201
        assert response.json()["user"]["email"] == "user@example.com"
        assert "set-cookie" not in response.headers
        user = next(value for value in session.added if isinstance(value, User))
        assert user.email == "user@example.com"
        assert user.password_hash and user.password_hash.startswith("$argon2")
        assert PASSWORD_HASHER.verify("Correct9!A", user.password_hash)
        assert "Correct9!A" not in user.password_hash
        assert len(mail.messages) == 1
        assert "token=" in mail.messages[0].body
        action = next(value for value in session.added if isinstance(value, AuthActionToken))
        token = re.search(r"token=([^\s]+)", mail.messages[0].body).group(1)
        assert action.token_hash == hash_opaque_token(token)
        assert token not in action.token_hash
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_duplicate_registration_returns_generic_conflict(auth_settings):
    existing = User(id=uuid4(), email="user@example.com", is_active=True)
    session = FakeAuthSession(scalar_values=[existing])
    with pytest.raises(AuthenticationError) as error:
        await AuthService(
            session, settings=auth_settings, email_provider=MemoryEmailProvider()
        ).register(
            RegisterRequest(email="USER@example.com", password="Correct9!A"),
            Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/api/v1/auth/register",
                    "headers": [],
                    "client": ("127.0.0.1", 1234),
                    "scheme": "http",
                    "server": ("test", 80),
                    "query_string": b"",
                }
            ),
        )
    assert error.value.code == "REGISTRATION_UNAVAILABLE"
    assert session.added == []


@pytest.mark.asyncio
async def test_login_transport_controls_token_delivery(auth_settings):
    user = User(
        id=uuid4(),
        email="user@example.com",
        password_hash=PASSWORD_HASHER.hash("Correct9!A"),
        email_verified_at=datetime.now(UTC),
        is_active=True,
        created_at=datetime.now(UTC),
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
        }
    )
    mobile = await AuthService(
        FakeAuthSession(scalar_values=[user]), settings=auth_settings
    ).login(
        LoginRequest(email="user@example.com", password="Correct9!A", client="mobile"),
        request,
    )
    assert mobile.access_token and mobile.token_type == "Bearer"
    assert mobile.csrf_token is None
    assert "session_token" not in mobile.model_dump()

    web = await AuthService(
        FakeAuthSession(scalar_values=[user]), settings=auth_settings
    ).login(
        LoginRequest(email="user@example.com", password="Correct9!A", client="web"),
        request,
    )
    assert web.access_token is None
    assert web.csrf_token


def test_email_normalization_and_opaque_token_hashing():
    assert normalize_email("  User@Example.COM ") == "user@example.com"
    raw = "opaque-session-token"
    assert hash_opaque_token(raw) != raw
    assert len(hash_opaque_token(raw)) == 64


def test_password_strength_rejects_weak_values():
    from pydantic import ValidationError

    from app.schemas.auth import RegisterRequest

    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="weak")


def test_password_policy_allows_eight_to_twelve_characters_only():
    from pydantic import ValidationError

    RegisterRequest(email="user@example.com", password="aB3!xxxx")
    RegisterRequest(email="user@example.com", password="aB3!xxxxxxxx")
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="aB3!xxxxxxxxx")


def test_auth_migration_adds_legacy_safe_user_columns_and_token_tables():
    from pathlib import Path

    migration = Path(__file__).parents[1] / "alembic/versions/0008_authentication.py"
    content = migration.read_text()
    for table in ("auth_sessions", "auth_action_tokens", "user_preferences"):
        assert f'"{table}"' in content
    assert "lower(email)" in content
    assert "token_hash" in content
    assert "nullable=True" in content


@pytest.mark.asyncio
async def test_invalid_login_uses_generic_error(monkeypatch, auth_settings):
    session = FakeAuthSession(scalar_values=[None])
    monkeypatch.setattr("app.services.auth.get_settings", lambda: auth_settings)

    async def fake_db():
        yield session

    from app.db.session import get_db

    app.dependency_overrides[get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "missing@example.com", "password": "Correct9!A"},
            )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
        assert response.json()["error"]["message"] == "Invalid email or password"
    finally:
        app.dependency_overrides.clear()


def test_auth_rate_limiter_blocks_brute_force_window():
    import asyncio

    limiter = InMemoryAuthRateLimiter(Settings(auth_login_rate_limit_attempts=1))
    assert asyncio.run(limiter.check("ip:email")).allowed
    assert not asyncio.run(limiter.check("ip:email")).allowed


@pytest.mark.asyncio
async def test_password_reset_consumes_token_and_revokes_sessions(auth_settings):
    user = User(
        id=uuid4(),
        email="user@example.com",
        password_hash=PASSWORD_HASHER.hash("OldPassword9!"),
        is_active=True,
    )
    raw_token = "reset-token-with-more-than-twenty-characters"
    action = AuthActionToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_opaque_token(raw_token),
        purpose="password_reset",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    session = FakeAuthSession(scalar_values=[action], user=user)
    await AuthService(session, settings=auth_settings).reset_password(
        raw_token, "New9!Pass"
    )
    assert action.used_at is not None
    assert PASSWORD_HASHER.verify("New9!Pass", user.password_hash)
    assert not PASSWORD_HASHER.verify("OldPassword9!", user.password_hash)


@pytest.mark.asyncio
async def test_cookie_auth_requires_csrf_header_and_rejects_expired_sessions(
    monkeypatch, auth_settings
):
    user = User(
        id=uuid4(),
        email="user@example.com",
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )
    session = AuthSession(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_opaque_token("session-token"),
        csrf_token_hash=hash_opaque_token("csrf-token"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    fake = FakeAuthSession(scalar_values=[session], user=user)
    monkeypatch.setattr("app.services.auth.get_settings", lambda: auth_settings)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/logout",
            "headers": [
                (b"host", b"test"),
                (b"cookie", b"lingua_session=session-token; lingua_csrf=csrf-token"),
            ],
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
        }
    )
    with pytest.raises(AuthenticationError) as error:
        await get_auth_context(request, fake)
    assert error.value.code == "CSRF_FAILED"

    expired = FakeAuthSession(scalar_values=[None])
    with pytest.raises(AuthenticationError) as error:
        await get_auth_context(request, expired)
    assert error.value.code == "AUTHENTICATION_REQUIRED"
