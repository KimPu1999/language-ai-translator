# Phase 2B — Translation Reliability

## Reliability controls

- Text and detection requests are NFC-normalized and limited to 5,000 Unicode characters. Counts are not byte counts, so Burmese input is handled consistently.
- Translation and detection are rejected with `429` when the configured per-client request or character window is exceeded. Defaults are 60 requests and 100,000 characters per 60 seconds. The current limiter is process-local; deploy behind a shared limiter before running multiple API instances.
- Every response includes `X-Request-ID`; structured errors also include the same ID in `error.request_id`.
- Provider timeouts map to `504 TRANSLATION_PROVIDER_TIMEOUT`; network failures map to `503`, credential failures to `502`, rate limits to `429`, and upstream HTTP failures to `502`/`503`.
- Capabilities are derived from the configured provider adapter rather than assumed from configuration alone.

## Usage and privacy

`translation_usage_events` records request ID, operation, provider, language codes, Unicode character count, status, latency, error code, and timestamp. It does not contain source text, translated text, user identity, or secrets. Usage recording is best-effort so telemetry outages cannot change the translation response.

Translation endpoints do not create history records. There are no unauthenticated history or favorite APIs.

## Optional cache

Caching is disabled by default (`TRANSLATION_CACHE_ENABLED=false`). When explicitly enabled, `REDIS_URL` is required and the Redis adapter is selected through `app.cache.factory`; no provider fallback is enabled. Cache rollout should be reviewed for the sensitivity of translated content before production use.

The Google adapter is an unregistered interface seam only. It cannot be selected as a fallback until separately configured and tested.

## Migration and checks

```bash
cd services/api
alembic upgrade head
ruff check .
python -m pytest -q
```

The migration is `0002_translation_usage_events`, following the Phase 1A schema and preserving PostgreSQL-only operation.
