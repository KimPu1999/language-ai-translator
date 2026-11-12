# Lingua AI Translator — Phase 4A

Phase 3A adds the Azure Speech provider foundation on top of the Phase 2 translation reliability controls. Speech recognition and synthesis use injectable interfaces, locale-aware capability metadata, server-only credentials, and bounded thread-offloaded SDK calls. No speech capture or upload product flow is enabled in this phase.

## Run locally

1. Copy `.env.example` to `.env`, replace the database placeholders, and never commit the file.
2. Install dependencies: `python -m pip install -r services/api/requirements.txt`.
3. Run migrations: `cd services/api && alembic upgrade head`.
4. Start the API: `uvicorn app.main:app --app-dir services/api --reload`.
5. Run checks: `pytest` and `ruff check .`.

Web and mobile setup details are documented in [docs/local-development.md](docs/local-development.md).

The API exposes `GET /health/live`, `GET /health/ready`, `GET /api/v1/languages`, `GET /api/v1/capabilities`, `GET /api/v1/speech/capabilities`, and `POST /api/v1/translations/text`.

Phase 3B adds `POST /api/v1/voice/transcribe` for bounded raw audio requests and `POST /api/v1/voice/synthesize` for inline WAV responses. See [docs/phase-3b.md](docs/phase-3b.md) for request formats and FFmpeg requirements.

Phase 2A also exposes `POST /api/v1/translations/detect`. Azure configuration and response/error behavior are documented in [docs/phase-2a.md](docs/phase-2a.md). Phase 2B details are in [docs/phase-2b.md](docs/phase-2b.md).

Speech configuration and locale mappings are documented in [docs/phase-3a.md](docs/phase-3a.md).

Phase 4A/4B adds `GET /api/v1/ocr/capabilities` and multipart `POST /api/v1/ocr/extract?language=<code>`. OCR accepts JPEG, PNG, and WebP up to 8 MB and 20 MP, validates signatures, strips EXIF metadata after orientation, returns Unicode text and normalized bounding boxes, enforces OCR quotas, and retains no images. Tesseract capabilities are limited to language packs actually installed on the API host. See [docs/phase-4a.md](docs/phase-4a.md) and [docs/phase-4b.md](docs/phase-4b.md).

Phase 4E adds an optional Google Cloud Vision adapter. Tesseract remains the default; Google is selected only with explicit server configuration and per-request cloud consent. Burmese support is experimental, and cloud usage records billable metadata only.

Phase 5A adds bounded PDF, DOCX, and UTF-8 TXT extraction at `/api/v1/documents`. Extraction is review-only, supports structured blocks and OCR fallback for scanned PDF pages, and never translates or stores document contents. See [docs/phase-5a.md](docs/phase-5a.md).

Phase 5B adds a disabled-by-default Celery/Redis document job system with private storage, PostgreSQL job ownership, expiration, cancellation, retries, and metadata-only usage records. See [docs/phase-5b.md](docs/phase-5b.md). Authentication is not yet implemented, so only the explicitly enabled development guest capability flow is available.

## Current scope

The repository is organized as `apps/web`, `apps/mobile`, `services/api`, `packages/contracts`, `infra`, and `docs`. History and user records have no public endpoints, there are no auth endpoints, source/translated text is not stored by translation requests, and the API refuses non-PostgreSQL URLs.

