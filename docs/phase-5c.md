# Phase 5C: Translation and export

Document jobs retain ordered, reviewable segment objects. A client must
explicitly confirm reviewed source text before calling
`POST /api/v1/documents/{id}/translate`. Translation runs in the existing
Celery worker through the Phase 2 provider registry; without a configured
provider, extraction and review remain available and translation returns a
structured 503.

Completed segment translations are persisted with progress, so retries skip
segments that already have a provider result. TXT, DOCX and reflowed PDF
exporters are available through the ownership-checked private download route:

`GET /api/v1/documents/{id}/download`

PDF output uses a Unicode TTF when `DOCUMENT_PDF_FONT_PATH` is configured or a
safe system fallback is found. Configure a Burmese-capable font such as Noto
Sans Myanmar for production. PDF output is paginated and readable, not a
pixel-perfect replacement of the source layout. Generated files are deleted
when their job expires or is deleted.

Migration `0007_document_translation` adds translation state, output metadata
and non-sensitive provider/character usage fields.
