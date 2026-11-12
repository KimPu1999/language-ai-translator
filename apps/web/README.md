# Lingua Web — Phase 1B

React + TypeScript + Vite web client for the Phase 1A FastAPI service. It uses Tailwind CSS, Lucide icons, React Router, TanStack Query, Zustand, i18next, Vitest, and Testing Library.

## Run

```bash
cp .env.example .env
npm install
npm run dev
```

Set `VITE_API_BASE_URL` to the FastAPI origin. The default is `http://localhost:8000`.

## Verify

```bash
npm run build
npm test
```

Phase 1B deliberately does not fake functionality: the backend’s configured-provider state is surfaced, translation 503s are shown as actionable errors, and Voice, Camera, Documents, History, and Favorites clearly explain their current unavailable/non-persistent status.

