# Phase 4B — OCR API integration and security

Phase 4B hardens the Phase 4A OCR endpoint with streaming file-size enforcement, MIME/signature agreement, EXIF-stripped RGB preprocessing, bounded OCR execution, OCR-specific in-memory quotas, and metadata-only usage events.

`ocr_usage_events` stores request ID, provider, language, dimensions, file size, execution time, status, error code, and timestamp only. It never stores image bytes or extracted text. The image is closed after each request and no user history endpoint is involved.

Translation is intentionally not part of the OCR endpoint. Clients must display the OCR response for user review and then make a separate, explicit Phase 2 translation request subject to the existing 5,000-character limit.

Cloud OCR remains disabled unless explicitly configured. Tesseract is selected only when the executable, Python adapter, and required traineddata pack are available.

## Optional Google Cloud Vision (Phase 4E)

Google Cloud Vision is never a fallback. Set `OCR_PROVIDER=google-cloud-vision` and `OCR_GOOGLE_CLOUD_ENABLED=true` explicitly, then install `services/api/requirements-ocr-cloud.txt`. Prefer Application Default Credentials or workload identity in production; `OCR_GOOGLE_CLOUD_CREDENTIALS_JSON` is a server-only secret option. Credentials are never returned to clients.

When selected, `GET /api/v1/ocr/capabilities` reports `consent_required: true` and marks Burmese (`my`) as experimental. `POST /api/v1/ocr/extract` requires multipart `cloud_consent=true`; without it, the image is rejected before provider processing. The client must disclose that the image will leave the server before collecting consent. A cloud configuration failure returns provider-unavailable; it does not trigger a silent Google fallback. Cloud requests record metadata-only `billable_units`; no image or extracted text is retained.
