# Local development

## Backend

1. Copy `.env.example` to `.env` and set a real PostgreSQL `DATABASE_URL`; never commit the file.
2. Start PostgreSQL with `docker compose -f infra/docker-compose.yml up -d` after setting `POSTGRES_USER` and `POSTGRES_PASSWORD` in `.env`.
3. Install Python dependencies with `python -m pip install -r services/api/requirements.txt`.
4. Apply migrations from `services/api`: `alembic upgrade head`.
5. Start the API from the repository root: `uvicorn app.main:app --app-dir services/api --reload`.

## Web

From `apps/web`, copy `.env.example` to `.env`, run `npm ci`, then `npm run dev`. Use `npm run lint`, `npm test -- --run`, and `npm run build` for verification.

## Mobile

From `apps/mobile`, install Flutter 3.24+ and run `flutter pub get`, `flutter analyze`, and `flutter test`. Pass the API URL with `flutter run --dart-define=API_BASE_URL=...`:

- Android emulator: `http://10.0.2.2:8000`
- iOS simulator: `http://localhost:8000`
- Physical device: the development machine’s LAN hostname or IP

Older macOS/Xcode environments should use a Flutter SDK compatible with the installed Xcode. Device signing and native platform builds require local Apple/Android toolchains and are not covered by this repository-only setup.

