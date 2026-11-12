# Phase 5A — Document Extraction Foundation

The API exposes:

- `GET /api/v1/documents/capabilities`
- `POST /api/v1/documents/extract?source_language=<code>`

The extraction endpoint accepts PDF, DOCX, and UTF-8 TXT uploads. It returns structured blocks, extracted text, page count, pages processed by OCR, and 3,000-character review segments. It never calls translation and does not persist the upload or extracted text.

Default limits are 10 MB per upload, 30 PDF pages, 50,000 extracted characters, and 3,000 characters per review segment. PDF text layers are extracted with `pypdf`; pages without text require a configured existing OCR provider and are rendered with `pypdfium2`. DOCX paragraphs, headers, footers, tables, and nested table cells are returned in document order where supported.

DOCX archives are checked before parsing for macro payloads, excessive entries, excessive uncompressed size, and unsafe compression ratios. Password-protected PDFs and unsupported encodings/formats are rejected with structured errors.

Install the document dependencies with the normal API requirements:

```bash
python -m pip install -r services/api/requirements.txt
```

OCR fallback remains subject to the existing OCR provider configuration and capability reporting. A scanned PDF does not silently fabricate text or switch to a cloud provider.
