# Lingua Web — Phase 4C

React + TypeScript + Vite web client for the FastAPI translation service. It uses Tailwind CSS, Lucide icons, React Router, TanStack Query, Zustand, i18next, Vitest, and Testing Library.

## Run

```bash
cp .env.example .env
npm install
npm run dev
```

Set `VITE_API_BASE_URL` to the FastAPI origin. The default is `http://localhost:8000`. The browser only calls the FastAPI API; provider credentials never belong in Vite environment variables.

Translation uses the live language and capability endpoints, supports Auto Detect, and sends the source language as `null` when automatic detection is selected. Voice uses the live speech capability endpoint, browser `MediaRecorder`, the Phase 3B voice endpoints, and inline WAV playback. Provider failures, rate limits, timeouts, permission failures, and network failures remain visible as actionable UI errors; the client never invents output.

## Document translation

The `/documents` route uses the private Phase 5B/5C document APIs. It validates PDF, DOCX, and UTF-8 TXT files in the browser, shows upload and server job progress, polls only while a job is active, and requires an explicit edited-text review before translation. Extracted content is rendered as plain text, never as HTML. Downloads use a short-lived browser object URL that is revoked after use.

The backend currently returns one translated artifact in the uploaded document's original format. The UI enables the matching PDF, DOCX, or TXT download control and leaves other format controls disabled rather than claiming a conversion the API did not perform.

For the backend's local-development-only guest capability flow, `VITE_DOCUMENT_CAPABILITY_TOKEN` may be set to the same local token as `DOCUMENT_GUEST_CAPABILITY_TOKEN`. This value is sent to the browser by design for local development only; do not place production credentials or personal access tokens in Vite variables.

History and favorites are local-only and opt-in from Settings. Nothing is stored automatically. Disabling the option clears the locally stored entries.

## Verify

```bash
npm run build
npm test
```

Voice recording begins only after an explicit user action, is capped at 15 seconds, and is cleaned up on stop, cancel, navigation, and unmount. Audio and transcripts are not saved automatically. Camera OCR is available through the FastAPI OCR endpoints; Documents remains clearly unavailable, and no unauthorized personal history API is used.

## Camera/image translation

The `/camera` route accepts JPEG, PNG, and WebP uploads or explicit browser camera capture. It validates size and decoded dimensions client-side, supports crop/rotate controls, revokes temporary preview URLs, and stops camera tracks after capture or navigation. OCR capabilities and results come from FastAPI only. Extracted text is editable and must be explicitly reviewed before a separate Phase 2 translation request. Images are never saved automatically, and OCR/translation errors remain separate and retryable.

## Two-way conversation

`/conversation` provides Person A and Person B profiles with independent speech languages, target languages, and voices. Each turn is assigned a unique ID, recorded with push-to-talk for up to 15 seconds, transcribed, editable, translated, and optionally synthesized for replay. A second microphone cannot start while another is recording or while audio is playing. Ending or clearing a session invalidates in-flight responses; clear also revokes temporary audio URLs. Only explicit local saves persist text when local saving is enabled. There is no cloud synchronization or full-duplex streaming.

