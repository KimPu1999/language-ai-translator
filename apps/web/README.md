# Lingua Web — Phase 2C

React + TypeScript + Vite web client for the FastAPI translation service. It uses Tailwind CSS, Lucide icons, React Router, TanStack Query, Zustand, i18next, Vitest, and Testing Library.

## Run

```bash
cp .env.example .env
npm install
npm run dev
```

Set `VITE_API_BASE_URL` to the FastAPI origin. The default is `http://localhost:8000`. The browser only calls the FastAPI API; provider credentials never belong in Vite environment variables.

Translation uses the live language and capability endpoints, supports Auto Detect, and sends the source language as `null` when automatic detection is selected. Provider failures, rate limits, timeouts, and network failures remain visible as retryable UI errors; the client never invents output.

History and favorites are local-only and opt-in from Settings. Nothing is stored automatically. Disabling the option clears the locally stored entries.

## Verify

```bash
npm run build
npm test
```

Phase 2C deliberately does not fake functionality: the backend’s configured-provider state is surfaced, translation failures are shown as actionable errors, and Voice, Camera, and Documents remain clearly unavailable. No unauthorized personal history API is used.

