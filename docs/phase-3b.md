# Phase 3B — Real Voice Processing

The API now exposes:

- `POST /api/v1/voice/transcribe?locale=en-US` with the recorded audio bytes as the request body and an allowed audio `Content-Type` (`audio/wav`, `audio/webm`, `audio/ogg`, `audio/mpeg`, or `audio/mp4`).
- `POST /api/v1/voice/synthesize` with JSON `{ "text": "...", "locale": "my-MM", "voice": "my-MM-NilarNeural" }`.

Transcription accepts at most 5 MB and 15 seconds. FFprobe validates duration and FFmpeg converts content to mono 16 kHz PCM WAV before Azure Speech recognition. Temporary files are created under a request-scoped temporary directory and removed on success and failure. Conversion uses fixed argument lists with `shell=False`.

Synthesis returns `audio/wav` bytes inline; it does not create public audio URLs. Both operations use request and byte/character limits and record only metadata in `speech_usage_events`. Audio, text, and transcripts are never written to logs or usage records.

The endpoints return structured errors with request IDs. Azure credentials remain backend-only. Live Azure calls require both `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`, and the server must have `ffmpeg` and `ffprobe` installed.
