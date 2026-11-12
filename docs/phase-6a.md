# Phase 6A — Secure Authentication Backend

Phase 6A adds first-party accounts to the FastAPI backend without changing the
Phase 1–5 translation, OCR, speech, or document contracts.

## Account lifecycle

- `POST /api/v1/auth/register` creates an account and sends a verification
  message. Registration never signs the account in before email verification.
- `POST /api/v1/auth/verify-email` consumes a single-use verification token.
- `POST /api/v1/auth/resend-verification` resends verification instructions
  without revealing whether an address exists.
- `POST /api/v1/auth/login` authenticates a verified account.
- `POST /api/v1/auth/forgot-password` and
  `POST /api/v1/auth/reset-password` implement expiring, single-use password
  reset actions.
- `GET /api/v1/auth/me` returns the authenticated account.
- `POST /api/v1/auth/logout`, `GET /api/v1/auth/sessions`, and
  `DELETE /api/v1/auth/sessions/{id}` manage server-side sessions.

## Session transports

Web clients use an HttpOnly `lingua_session` cookie and a readable,
session-bound `lingua_csrf` cookie. Unsafe cookie-authenticated requests must
send the same value in `X-CSRF-Token`, and configured Origins are checked.
Production must use HTTPS and `AUTH_COOKIE_SECURE=true`.

Mobile clients send `client=mobile` during login and receive an opaque Bearer
token. The token is only returned to that client transport and only its SHA-256
hash is stored in PostgreSQL. Mobile applications must store it in platform
secure storage.

## Storage and email

Migration `0008_authentication` adds nullable account columns so existing
Phase 1 user rows remain valid. A PostgreSQL functional unique index enforces
case-insensitive email uniqueness. Passwords use `pwdlib` Argon2; session and
action tokens are random, single-use/expiring where applicable, and hashed at
rest.

SMTP delivery is pluggable. In development, `AUTH_DEV_MAILBOX_DIR` can write
private `.eml` files for local testing; this is disabled outside development
and is not an HTTP mail-preview endpoint. Without SMTP or the explicit
development mailbox, action-email requests fail with a structured unavailable
error rather than claiming delivery.

Authentication attempts use Redis when `REDIS_URL` is configured and otherwise
use a process-local development fallback. Production deployments should use
Redis and HTTPS; a Redis limiter outage fails closed.
