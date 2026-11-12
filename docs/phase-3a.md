# Phase 3A — Azure Speech Foundation

Phase 3A adds a provider boundary for Azure Speech recognition and synthesis. It does not add microphone, camera, upload, authentication, or speech history endpoints.

## Configuration

Set both values in the API environment to configure Azure Speech:

```dotenv
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_SPEECH_TIMEOUT_SECONDS=30
```

The API rejects a partially configured credential pair. Keys are read only by the backend and are never included in the capability response.

Install the API requirements, including `azure-cognitiveservices-speech`, before invoking a provider:

```bash
python -m pip install -r services/api/requirements.txt
```

## Capability metadata

`GET /api/v1/speech/capabilities` returns configured status, per-language STT/TTS availability, and Azure voice metadata. Text language codes intentionally remain separate from speech locales:

| Text code | Speech locale |
| --- | --- |
| `my` | `my-MM` |
| `en` | `en-US` |
| `th` | `th-TH` |
| `zh-Hans` | `zh-CN` |
| `ja` | `ja-JP` |
| `ko` | `ko-KR` |

Provider SDK calls are blocking, so recognition and synthesis are executed with `asyncio.to_thread` and bounded by `AZURE_SPEECH_TIMEOUT_SECONDS`. Provider errors use stable codes and do not include SDK details or credentials.

The recognition and synthesis interfaces are injectable. Phase 3B adds `POST /api/v1/voice/transcribe` and `POST /api/v1/voice/synthesize`; audio is returned inline and is never published as a URL.
