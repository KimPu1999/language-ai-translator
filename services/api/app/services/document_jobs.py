from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_errors import AuthenticationError
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.auth import get_auth_context


def owner_from_capability_token(token: str | None, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if (
        not settings.document_jobs_enabled
        or not settings.document_guest_mode_enabled
        or settings.app_env.lower() != "development"
        or not settings.document_guest_capability_token
        or not token
    ):
        raise HTTPException(status_code=404, detail="Document jobs are unavailable")
    expected = settings.document_guest_capability_token.get_secret_value().encode()
    supplied = token.encode()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=404, detail="Document jobs are unavailable")
    digest = hashlib.sha256(supplied).hexdigest()
    return f"guest:{digest}"


async def require_document_owner(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_document_capability_token: str | None = Header(default=None),
) -> str:
    settings = get_settings()
    if not settings.document_jobs_enabled:
        raise HTTPException(status_code=404, detail="Document jobs are unavailable")
    has_session = bool(
        request.headers.get("authorization")
        or request.cookies.get(settings.auth_cookie_name)
    )
    if has_session:
        try:
            context = await get_auth_context(request, db)
        except AuthenticationError:
            # An invalid or expired session must never fall back to a guest token.
            raise
        return f"user:{context.user.id}"
    return owner_from_capability_token(x_document_capability_token)


def expiration(settings: Settings | None = None) -> datetime:
    settings = settings or get_settings()
    return datetime.now(UTC) + timedelta(hours=settings.document_job_expiration_hours)


def parse_job_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Document job not found") from exc
