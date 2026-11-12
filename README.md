# Lingua AI Translator — Phase 2B

Phase 2B adds reliability controls around the Phase 2A Azure Translator integration: capability-aware provider selection, Unicode-safe limits, request/character rate limits, request IDs, bounded timeout mapping, and metadata-only usage events. Azure credentials are never sent to clients, and translation text is not persisted by the translation endpoints.

## Run locally

1. Copy `.env.example` to `.env`, replace the database placeholders, and never commit the file.
2. Install dependencies: `python -m pip install -r services/api/requirements.txt`.
3. Run migrations: `cd services/api && alembic upgrade head`.
4. Start the API: `uvicorn app.main:app --app-dir services/api --reload`.
5. Run checks: `pytest` and `ruff check .`.

Web and mobile setup details are documented in [docs/local-development.md](docs/local-development.md).

The API exposes `GET /health/live`, `GET /health/ready`, `GET /api/v1/languages`, `GET /api/v1/capabilities`, and `POST /api/v1/translations/text`.

Phase 2A also exposes `POST /api/v1/translations/detect`. Azure configuration and response/error behavior are documented in [docs/phase-2a.md](docs/phase-2a.md). Phase 2B details are in [docs/phase-2b.md](docs/phase-2b.md).

## Current scope

The repository is organized as `apps/web`, `apps/mobile`, `services/api`, `packages/contracts`, `infra`, and `docs`. History and user records have no public endpoints, there are no auth endpoints, source/translated text is not stored by translation requests, and the API refuses non-PostgreSQL URLs.

