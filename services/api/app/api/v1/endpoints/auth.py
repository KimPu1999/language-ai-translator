from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_errors import AuthenticationError
from app.core.auth_rate_limit import (
    InMemoryAuthRateLimiter,
    get_auth_action_rate_limiter,
    get_auth_rate_limiter,
)
from app.core.config import get_settings
from app.core.errors import error_payload
from app.db.session import get_db
from app.schemas.auth import (
    AuthMessageResponse,
    AuthResponse,
    CsrfResponse,
    EmailActionRequest,
    LoginRequest,
    RegisterRequest,
    RegistrationResponse,
    ResetPasswordRequest,
    SessionResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth import (
    AuthContext,
    AuthService,
    clear_auth_cookies,
    get_auth_context,
    set_auth_cookies,
    validate_origin,
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _rate_limited(request: Request, retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=error_payload(
            "AUTH_RATE_LIMITED",
            "Too many authentication attempts. Try again later.",
            request_id=request.state.request_id,
        ),
        headers={"Retry-After": str(retry_after)},
    )


def _rate_key(request: Request, email: str | None = None) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}:{email.casefold() if email else '-'}"


async def _current_auth(
    request: Request, db: AsyncSession = Depends(get_db)
) -> AuthContext:
    return await get_auth_context(request, db)


async def _check_rate_limit(limiter, key: str):
    try:
        return await limiter.check(key)
    except Exception as exc:
        # A configured distributed limiter failing closed is safer than silently
        # bypassing brute-force protection.
        raise AuthenticationError(
            "AUTH_RATE_LIMITER_UNAVAILABLE",
            "Authentication is temporarily unavailable",
            status_code=503,
        ) from exc


@router.post("/register", response_model=RegistrationResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    limiter: InMemoryAuthRateLimiter = Depends(get_auth_action_rate_limiter),
) -> RegistrationResponse:
    validate_origin(request)
    decision = await _check_rate_limit(limiter, _rate_key(request, str(payload.email)))
    if not decision.allowed:
        return _rate_limited(request, decision.retry_after)
    del response
    return await AuthService(db).register(payload, request)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    limiter: InMemoryAuthRateLimiter = Depends(get_auth_rate_limiter),
) -> AuthResponse:
    validate_origin(request)
    email = str(payload.email).casefold()
    decision = await _check_rate_limit(limiter, _rate_key(request, email))
    if not decision.allowed:
        return _rate_limited(request, decision.retry_after)
    result = await AuthService(db).login(payload, request)
    if result.session_token:
        await limiter.clear(_rate_key(request, email))
    if result.csrf_token:
        set_auth_cookies(
            response, _session_token_from_response(result), result.csrf_token, get_settings()
        )
    return result


@router.post("/logout", response_model=AuthMessageResponse)
async def logout(
    response: Response,
    context: AuthContext = Depends(_current_auth),
    db: AsyncSession = Depends(get_db),
) -> AuthMessageResponse:
    await AuthService(db).logout(context)
    clear_auth_cookies(response, get_settings())
    return AuthMessageResponse(message="Signed out")


@router.get("/me", response_model=UserResponse)
async def current_user(context: AuthContext = Depends(_current_auth)) -> UserResponse:
    return UserResponse(
        id=context.user.id,
        email=context.user.email,
        email_verified=context.user.email_verified_at is not None,
        is_active=context.user.is_active,
        created_at=context.user.created_at,
    )


@router.get("/csrf", response_model=CsrfResponse)
async def csrf_token(
    request: Request,
    response: Response,
    context: AuthContext = Depends(_current_auth),
    db: AsyncSession = Depends(get_db),
) -> CsrfResponse:
    validate_origin(request)
    token = await AuthService(db).refresh_csrf(context)
    response.set_cookie(
        get_settings().auth_csrf_cookie_name,
        token,
        max_age=get_settings().auth_session_ttl_seconds,
        httponly=False,
        secure=get_settings().auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return CsrfResponse(csrf_token=token)


@router.get("/sessions", response_model=list[SessionResponse])
async def sessions(
    context: AuthContext = Depends(_current_auth), db: AsyncSession = Depends(get_db)
) -> list[SessionResponse]:
    return await AuthService(db).list_sessions(context)


@router.delete("/sessions/{session_id}", response_model=AuthMessageResponse)
async def revoke_session(
    session_id: UUID,
    context: AuthContext = Depends(_current_auth),
    db: AsyncSession = Depends(get_db),
) -> AuthMessageResponse:
    await AuthService(db).revoke_session(context, session_id)
    return AuthMessageResponse(message="Session revoked")


@router.post("/verify-email", response_model=AuthMessageResponse)
async def verify_email(
    payload: VerifyEmailRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    validate_origin(request)
    await AuthService(db).verify_email(payload.token)
    return AuthMessageResponse(message="Email verified")


@router.post("/resend-verification", response_model=AuthMessageResponse, status_code=202)
async def resend_verification(
    payload: EmailActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    limiter: InMemoryAuthRateLimiter = Depends(get_auth_action_rate_limiter),
) -> AuthMessageResponse | JSONResponse:
    validate_origin(request)
    decision = await _check_rate_limit(limiter, _rate_key(request, str(payload.email)))
    if not decision.allowed:
        return _rate_limited(request, decision.retry_after)
    await AuthService(db).resend_verification(payload)
    return AuthMessageResponse(message="If the account exists, a verification email will be sent")


@router.post("/forgot-password", response_model=AuthMessageResponse, status_code=202)
async def forgot_password(
    payload: EmailActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    limiter: InMemoryAuthRateLimiter = Depends(get_auth_action_rate_limiter),
) -> AuthMessageResponse | JSONResponse:
    validate_origin(request)
    decision = await _check_rate_limit(limiter, _rate_key(request, str(payload.email)))
    if not decision.allowed:
        return _rate_limited(request, decision.retry_after)
    await AuthService(db).request_password_reset(payload)
    return AuthMessageResponse(message="If the account exists, reset instructions will be sent")


@router.post("/reset-password", response_model=AuthMessageResponse)
async def reset_password(
    payload: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> AuthMessageResponse:
    validate_origin(request)
    await AuthService(db).reset_password(payload.token, payload.password)
    return AuthMessageResponse(message="Password reset successfully")


def _session_token_from_response(result: AuthResponse) -> str:
    if not result.session_token:
        raise RuntimeError("session token was not issued")
    return result.session_token
