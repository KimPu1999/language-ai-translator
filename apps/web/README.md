# Lingua Web — Phase 3E

React + TypeScript + Vite web client for the FastAPI translation service. It uses Tailwind CSS, Lucide icons, React Router, TanStack Query, Zustand, i18next, Vitest, and Testing Library.

## Run

```bash
cp .env.example .env
npm install
npm run dev
```

Set `VITE_API_BASE_URL` to the FastAPI origin. The default is `http://localhost:8000`. The browser only calls the FastAPI API; provider credentials never belong in Vite environment variables.

Translation uses the live language and capability endpoints, supports Auto Detect, and sends the source language as `null` when automatic detection is selected. Voice uses the live speech capability endpoint, browser `MediaRecorder`, the Phase 3B voice endpoints, and inline WAV playback. Provider failures, rate limits, timeouts, permission failures, and network failures remain visible as actionable UI errors; the client never invents output.

History and favorites are local-only and opt-in from Settings. Nothing is stored automatically. Disabling the option clears the locally stored entries.

## Verify

```bash
npm run build
npm test
```

Voice recording begins only after an explicit user action, is capped at 15 seconds, and is cleaned up on stop, cancel, navigation, and unmount. Audio and transcripts are not saved automatically. Camera and Documents remain clearly unavailable, and no unauthorized personal history API is used.

## Two-way conversation

`/conversation` provides Person A and Person B profiles with independent speech languages, target languages, and voices. Each turn is assigned a unique ID, recorded with push-to-talk for up to 15 seconds, transcribed, editable, translated, and optionally synthesized for replay. A second microphone cannot start while another is recording or while audio is playing. Ending or clearing a session invalidates in-flight responses; clear also revokes temporary audio URLs. Only explicit local saves persist text when local saving is enabled. There is no cloud synchronization or full-duplex streaming.

