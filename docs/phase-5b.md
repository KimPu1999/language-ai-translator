# Phase 5B — Secure Document Job System

Document jobs are disabled by default. Authenticated Phase 6A sessions own document jobs with a server-derived `user:<uuid>` subject. For local development without an account, the API refuses document-job requests unless all of the following guest-only conditions are true:

```env
APP_ENV=development
REDIS_URL=redis://localhost:6379/0
DOCUMENT_JOBS_ENABLED=true
DOCUMENT_GUEST_MODE_ENABLED=true
DOCUMENT_GUEST_CAPABILITY_TOKEN=<local-only-random-token>
```

The guest capability token is accepted through `X-Document-Capability-Token` and is hashed into the job owner subject. The guest mode validator rejects non-development environments. Authenticated requests take precedence; invalid sessions cannot fall back to the guest capability token.

## Worker processes

Run a worker and scheduler separately from FastAPI:

```bash
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --concurrency=2
celery -A app.tasks.celery_app.celery_app beat --loglevel=INFO
```

The worker performs Phase 5A extraction outside the request handler, uses idempotent status transitions, retries unexpected worker failures up to the configured limit, and records metadata-only usage events. Scheduled cleanup expires jobs after 24 hours and removes private files.

## API

- `POST /api/v1/documents` — enqueue a private upload; supports `Idempotency-Key`.
- `GET /api/v1/documents/{id}` — owner-only status.
- `GET /api/v1/documents/{id}/segments` — owner-only extracted review segments.
- `PUT /api/v1/documents/{id}/segments` — owner-only edited segments.
- `POST /api/v1/documents/{id}/cancel` — owner-only cancellation.
- `POST /api/v1/documents/{id}/retry` — owner-only bounded retry.
- `DELETE /api/v1/documents/{id}` — owner-only deletion and private-file cleanup.

There are no public download URLs. Files are stored under `DOCUMENT_STORAGE_ROOT` with random names and mode `0600`, outside the webroot. Application limits are enforced while reading the multipart stream; production reverse proxies must also enforce a request body limit of 10 MB before forwarding to FastAPI (for example, `client_max_body_size 10m` in Nginx). Extraction never logs document contents and never translates automatically.
