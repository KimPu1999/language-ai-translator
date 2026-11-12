# Phase 2A — Azure Translator

Phase 2A connects the API to Microsoft Azure Translator REST API v3.0 through an async HTTPX adapter. The Azure subscription key is server-only and is read from `AZURE_TRANSLATOR_KEY`; it is never returned to web or mobile clients.

## Configuration

Set these values in the API environment:

```dotenv
AZURE_TRANSLATOR_KEY=your-server-side-key
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
AZURE_TRANSLATOR_REGION=
AZURE_TRANSLATOR_TIMEOUT_SECONDS=10
```

The endpoint validator only permits HTTPS Azure Translator hosts: the global Translator endpoint or an `*.cognitiveservices.azure.com` resource endpoint. The region header is omitted unless `AZURE_TRANSLATOR_REGION` is configured. Timeouts are bounded to 60 seconds maximum.

## API

- `GET /api/v1/capabilities` reports whether Azure text translation and language detection are configured.
- `POST /api/v1/translations/text` accepts `source_language` optionally for automatic detection, `target_language`, and `text` up to 5,000 characters.
- `POST /api/v1/translations/detect` accepts text up to 5,000 characters and returns the detected language, confidence score, and Azure alternatives.

Supported application language codes are `en`, `my`, `th`, `zh-Hans`, `ja`, and `ko`. Phase 2A does not persist source or translated text.

