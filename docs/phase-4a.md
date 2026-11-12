# Phase 4A — OCR backend foundation

The OCR API is provider-backed and does not fabricate results. Tesseract is selected only when its executable, `pytesseract`, and at least one mapped traineddata pack are available. Google Cloud Vision is an intentionally disabled adapter and is not selected by default.

## Endpoints

- `GET /api/v1/ocr/capabilities` reports the configured provider and only application languages whose Tesseract packs are installed.
- `POST /api/v1/ocr/extract?language=en` accepts a multipart field named `image` and returns text, provider, language, request ID, and normalized `[0, 1]` bounding boxes.

Application-to-Tesseract mappings are `my=mya`, `en=eng`, `th=tha`, `zh-Hans=chi_sim`, `ja=jpn`, and `ko=kor`.

Uploads are limited to 8 MB, decoded images to 20 MP, and MIME/content formats to JPEG, PNG, and WebP. EXIF orientation is applied before OCR. Temporary image data is held in memory only; no image or OCR text is logged or persisted. OCR processing is bounded by `OCR_TIMEOUT_SECONDS` and does not execute shell commands or accept arbitrary paths.

Install the host dependencies separately from Python packages, for example the Tesseract binary and the required traineddata packs. The API will report unavailable capabilities when they are absent.

Configuration is in `.env.example`: `OCR_TESSERACT_COMMAND`, `OCR_TIMEOUT_SECONDS`, `OCR_MAX_UPLOAD_BYTES`, `OCR_MAX_PIXELS`, and `OCR_GOOGLE_CLOUD_ENABLED`.
