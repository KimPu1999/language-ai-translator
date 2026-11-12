from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from uuid import UUID

from fastapi import Request
from pwdlib import PasswordHash
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_errors import AuthenticationError
from app.core.config import Settings, get_settings
from app.models.auth_action_token import AuthActionToken
from app.models.auth_session import AuthSession
from app.models.user import User
from app.providers.email.base import EmailDeliveryError, EmailMessage, EmailProvider
from app.providers.email.registry import get_email_provider
from app.schemas.auth import (
    AuthResponse,
    EmailActionRequest,
    LoginRequest,
    RegisterRequest,
    RegistrationResponse,
    SessionResponse,
    UserResponse,
    validate_password_strength,
)

PASSWORD_HASHER = PasswordHash.recommended()
ACTION_EMAIL_VERIFICATION = "email_verification"
ACTION_PASSWORD_RESET = "password_reset"
SAFE_AUTH_ERROR = "Invalid email or password"


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession
    transport: str


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_response(user: User) -> UserResponse:
    if not user.email:
        raise AuthenticationError("ACCOUNT_UNAVAILABLE", "Account is unavailable", status_code=503)
    return UserResponse(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _validate_configured_password(password: str, settings: Settings) -> None:
    try:
        validate_password_strength(password)
    except ValueError as exc:
        raise AuthenticationError("WEAK_PASSWORD", str(exc), status_code=422) from exc
    if len(password) < settings.auth_password_min_length:
        raise AuthenticationError(
            "WEAK_PASSWORD",
            f"Password must be at least {settings.auth_password_min_length} characters",
            status_code=422,
        )


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings | None = None,
        email_provider: EmailProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.email_provider = email_provider or get_email_provider(self.settings)

    async def register(self, payload: RegisterRequest, request: Request) -> RegistrationResponse:
        _validate_configured_password(payload.password, self.settings)
        email = normalize_email(str(payload.email))
        existing = await self.db.scalar(select(User).where(func.lower(User.email) == email))
        if existing:
            raise AuthenticationError(
                "REGISTRATION_UNAVAILABLE",
                "This email cannot be registered",
                status_code=409,
            )
        user = User(
            email=email,
            password_hash=PASSWORD_HASHER.hash(payload.password),
            is_active=True,
        )
        self.db.add(user)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AuthenticationError(
                "REGISTRATION_UNAVAILABLE",
                "This email cannot be registered",
                status_code=409,
            ) from exc
        raw_token = await self._create_action_token(user.id, ACTION_EMAIL_VERIFICATION)
        await self.db.commit()
        await self._send_verification(email, raw_token)
        del request
        return RegistrationResponse(
            user=_user_response(user),
            message="Registration created; verify your email before signing in",
        )

    async def login(self, payload: LoginRequest, request: Request) -> AuthResponse:
        email = normalize_email(str(payload.email))
        user = await self.db.scalar(select(User).where(func.lower(User.email) == email))
        if not user or not user.password_hash or not user.is_active:
            raise AuthenticationError("INVALID_CREDENTIALS", SAFE_AUTH_ERROR)
        try:
            password_valid = PASSWORD_HASHER.verify(payload.password, user.password_hash)
        except Exception:
            password_valid = False
        if not password_valid:
            raise AuthenticationError("INVALID_CREDENTIALS", SAFE_AUTH_ERROR)
        if user.email_verified_at is None:
            raise AuthenticationError(
                "EMAIL_NOT_VERIFIED", "Verify your email before signing in", status_code=403
            )
        user.last_login_at = _now()
        session, access_token, csrf_token = await self._create_session(
            user, request, payload.client, payload.device_name
        )
        await self.db.commit()
        return self._auth_response(user, session, access_token, csrf_token)

    async def verify_email(self, token: str) -> None:
        action, user = await self._valid_action(token, ACTION_EMAIL_VERIFICATION)
        user.email_verified_at = _now()
        action.used_at = _now()
        await self.db.commit()

    async def resend_verification(self, payload: EmailActionRequest) -> None:
        email = normalize_email(str(payload.email))
        user = await self.db.scalar(
            select(User).where(and_(func.lower(User.email) == email, User.is_active.is_(True)))
        )
        if not user or user.email_verified_at is not None or not user.email:
            return
        raw_token = await self._create_action_token(user.id, ACTION_EMAIL_VERIFICATION)
        await self.db.commit()
        await self._send_verification(user.email, raw_token)

    async def request_password_reset(self, payload: EmailActionRequest) -> None:
        email = normalize_email(str(payload.email))
        user = await self.db.scalar(
            select(User).where(and_(func.lower(User.email) == email, User.is_active.is_(True)))
        )
        if not user or not user.email or not user.password_hash:
            return
        raw_token = await self._create_action_token(user.id, ACTION_PASSWORD_RESET)
        await self.db.commit()
        try:
            await self.email_provider.send(
                EmailMessage(
                    recipient=user.email,
                    subject="Reset your Lingua password",
                    body=(
                        "Use this one-time link to reset your password:\n\n"
                        f"{self.settings.auth_public_base_url}/reset-password?token={quote(raw_token)}\n\n"
                        "If you did not request this, you can ignore this message."
                    ),
                )
            )
        except EmailDeliveryError as exc:
            raise AuthenticationError(
                "AUTH_EMAIL_UNAVAILABLE",
                "Password reset email could not be sent",
                status_code=503,
            ) from exc

    async def reset_password(self, token: str, password: str) -> None:
        _validate_configured_password(password, self.settings)
        action, user = await self._valid_action(token, ACTION_PASSWORD_RESET)
        user.password_hash = PASSWORD_HASHER.hash(password)
        action.used_at = _now()
        await self.db.execute(
            update(AuthSession)
            .where(and_(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)))
            .values(revoked_at=_now())
        )
        await self.db.commit()

    async def logout(self, context: AuthContext) -> None:
        context.session.revoked_at = _now()
        await self.db.commit()

    async def list_sessions(self, context: AuthContext) -> list[SessionResponse]:
        now = _now()
        result = await self.db.scalars(
            select(AuthSession)
            .where(
                and_(
                    AuthSession.user_id == context.user.id,
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > now,
                )
            )
            .order_by(AuthSession.created_at.desc())
        )
        return [
            SessionResponse(
                id=session.id,
                device_name=session.device_name,
                user_agent=session.user_agent,
                created_at=session.created_at,
                last_seen_at=session.last_seen_at,
                expires_at=session.expires_at,
                current=session.id == context.session.id,
            )
            for session in result
        ]

    async def revoke_session(self, context: AuthContext, session_id: UUID) -> None:
        session = await self.db.scalar(
            select(AuthSession).where(
                and_(AuthSession.id == session_id, AuthSession.user_id == context.user.id)
            )
        )
        if not session:
            raise AuthenticationError("SESSION_NOT_FOUND", "Session not found", status_code=404)
        session.revoked_at = _now()
        await self.db.commit()

    async def refresh_csrf(self, context: AuthContext) -> str:
        raw_token = secrets.token_urlsafe(32)
        context.session.csrf_token_hash = hash_opaque_token(raw_token)
        await self.db.commit()
        return raw_token

    async def _create_action_token(self, user_id: UUID, purpose: str) -> str:
        raw_token = secrets.token_urlsafe(32)
        await self.db.execute(
            update(AuthActionToken)
            .where(
                and_(
                    AuthActionToken.user_id == user_id,
                    AuthActionToken.purpose == purpose,
                    AuthActionToken.used_at.is_(None),
                )
            )
            .values(used_at=_now())
        )
        self.db.add(
            AuthActionToken(
                user_id=user_id,
                token_hash=hash_opaque_token(raw_token),
                purpose=purpose,
                expires_at=_now() + timedelta(seconds=self.settings.auth_action_token_ttl_seconds),
            )
        )
        return raw_token

    async def _valid_action(self, token: str, purpose: str) -> tuple[AuthActionToken, User]:
        action = await self.db.scalar(
            select(AuthActionToken)
            .where(
                and_(
                    AuthActionToken.token_hash == hash_opaque_token(token),
                    AuthActionToken.purpose == purpose,
                    AuthActionToken.used_at.is_(None),
                    AuthActionToken.expires_at > _now(),
                )
            )
            .with_for_update()
        )
        if not action:
            raise AuthenticationError(
                "INVALID_ACTION_TOKEN", "The link is invalid or expired", status_code=400
            )
        user = await self.db.get(User, action.user_id)
        if not user or not user.is_active:
            raise AuthenticationError(
                "INVALID_ACTION_TOKEN", "The link is invalid or expired", status_code=400
            )
        return action, user

    async def _send_verification(self, email: str, raw_token: str) -> None:
        try:
            await self.email_provider.send(
                EmailMessage(
                    recipient=email,
                    subject="Verify your Lingua email",
                    body=(
                        "Use this one-time link to verify your email:\n\n"
                        f"{self.settings.auth_public_base_url}/verify-email?token={quote(raw_token)}\n\n"
                        "If you did not create this account, you can ignore this message."
                    ),
                )
            )
        except EmailDeliveryError as exc:
            raise AuthenticationError(
                "AUTH_EMAIL_UNAVAILABLE",
                "Verification email could not be sent",
                status_code=503,
            ) from exc

    async def _create_session(
        self,
        user: User,
        request: Request,
        client: str,
        device_name: str | None,
    ) -> tuple[AuthSession, str, str | None]:
        access_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        session = AuthSession(
            user_id=user.id,
            token_hash=hash_opaque_token(access_token),
            csrf_token_hash=hash_opaque_token(csrf_token),
            device_name=device_name.strip() if device_name else None,
            user_agent=request.headers.get("user-agent", "")[:512] or None,
            ip_address=_request_ip(request),
            expires_at=_now() + timedelta(seconds=self.settings.auth_session_ttl_seconds),
        )
        self.db.add(session)
        await self.db.flush()
        return session, access_token, csrf_token if client == "web" else None

    def _auth_response(
        self,
        user: User,
        session: AuthSession,
        access_token: str,
        csrf_token: str | None,
    ) -> AuthResponse:
        return AuthResponse(
            user=_user_response(user),
            access_token=access_token if csrf_token is None else None,
            token_type="Bearer" if csrf_token is None else None,
            csrf_token=csrf_token,
            expires_at=session.expires_at,
            session_token=access_token,
        )


async def get_auth_context(request: Request, db: AsyncSession) -> AuthContext:
    bearer = request.headers.get("authorization", "")
    cookie_token = request.cookies.get(get_settings().auth_cookie_name)
    if bearer.lower().startswith("bearer "):
        raw_token = bearer[7:].strip()
        transport = "bearer"
    elif cookie_token:
        raw_token = cookie_token
        transport = "cookie"
    else:
        raise AuthenticationError("AUTHENTICATION_REQUIRED", "Authentication required")
    if not raw_token or len(raw_token) > 256:
        raise AuthenticationError("AUTHENTICATION_REQUIRED", "Authentication required")
    session = await db.scalar(
        select(AuthSession).where(
            and_(
                AuthSession.token_hash == hash_opaque_token(raw_token),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > _now(),
            )
        )
    )
    if not session:
        raise AuthenticationError("AUTHENTICATION_REQUIRED", "Authentication required")
    user = await db.get(User, session.user_id)
    if not user or not user.is_active or not user.email:
        raise AuthenticationError("AUTHENTICATION_REQUIRED", "Authentication required")
    if transport == "cookie" and request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_header = request.headers.get("x-csrf-token", "")
        csrf_cookie = request.cookies.get(get_settings().auth_csrf_cookie_name, "")
        if (
            not csrf_header
            or not csrf_cookie
            or not hmac.compare_digest(csrf_header, csrf_cookie)
            or not hmac.compare_digest(hash_opaque_token(csrf_header), session.csrf_token_hash)
        ):
            raise AuthenticationError("CSRF_FAILED", "CSRF validation failed", status_code=403)
        validate_origin(request, required=True)
    session.last_seen_at = _now()
    await db.commit()
    return AuthContext(user=user, session=session, transport=transport)


def validate_origin(request: Request, *, required: bool = False) -> None:
    origin = request.headers.get("origin")
    if required and not origin:
        raise AuthenticationError("ORIGIN_NOT_ALLOWED", "Origin is required", status_code=403)
    if origin and origin not in get_settings().cors_origins:
        raise AuthenticationError("ORIGIN_NOT_ALLOWED", "Origin is not allowed", status_code=403)


def set_auth_cookies(response, access_token: str, csrf_token: str, settings: Settings) -> None:
    response.set_cookie(
        settings.auth_cookie_name,
        access_token,
        max_age=settings.auth_session_ttl_seconds,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.auth_csrf_cookie_name,
        csrf_token,
        max_age=settings.auth_session_ttl_seconds,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response, settings: Settings) -> None:
    response.delete_cookie(settings.auth_cookie_name, path="/")
    response.delete_cookie(settings.auth_csrf_cookie_name, path="/")
