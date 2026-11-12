from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import error_payload
from app.core.rate_limit import InMemoryDocumentJobRateLimiter, get_document_job_rate_limiter
from app.db.session import get_db
from app.models.document_job import DocumentJob
from app.providers.documents.base import DocumentExtractionError
from app.providers.translation.azure import SUPPORTED_LANGUAGE_CODES
from app.providers.translation.registry import get_translation_registry
from app.schemas.document_jobs import (
    DocumentJobResponse,
    DocumentSegmentsResponse,
    DocumentSegmentsUpdate,
    DocumentTranslationRequest,
)
from app.services.document_jobs import expiration, parse_job_id, require_document_owner
from app.services.document_storage import PrivateDocumentStorage
from app.services.documents import DocumentExtractionService, normalize_document_segments
from app.tasks.document_tasks import enqueue_document_extraction, enqueue_document_translation

router = APIRouter(prefix="/api/v1/documents", tags=["document-jobs"])


def _error(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, request_id=request.state.request_id),
    )


def _response(job: DocumentJob) -> DocumentJobResponse:
    return DocumentJobResponse.model_validate(job)


async def _owned(job_id: str, owner: str, db: AsyncSession) -> DocumentJob:
    job = await db.get(DocumentJob, parse_job_id(job_id))
    if job is None or job.owner_subject != owner:
        raise DocumentExtractionError(
            "DOCUMENT_NOT_FOUND", "Document job not found", status_code=404
        )
    if job.expires_at <= datetime.now(UTC) and job.status != "expired":
        if job.status != "cancelled":
            job.status = "expired"
        await db.commit()
        storage = PrivateDocumentStorage(get_settings().document_storage_root)
        storage.delete(job.storage_key)
        if job.output_storage_key:
            storage.delete(job.output_storage_key)
    return job


@router.post("", response_model=DocumentJobResponse, status_code=202)
async def create_job(
    request: Request,
    document: UploadFile = File(...),
    source_language: str | None = Form(default=None),
    owner: str = Depends(require_document_owner),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    limiter: InMemoryDocumentJobRateLimiter = Depends(get_document_job_rate_limiter),
) -> DocumentJobResponse | JSONResponse:
    settings = get_settings()
    decision = await limiter.check(owner)
    if not decision.allowed:
        return JSONResponse(
            status_code=429,
            content=error_payload(
                decision.code or "DOCUMENT_JOB_RATE_LIMIT_EXCEEDED",
                "Document job rate limit reached",
                request_id=request.state.request_id,
            ),
            headers={"Retry-After": str(decision.retry_after)},
        )
    if idempotency_key:
        idempotency_key = idempotency_key.strip()[:128]
        existing = await db.scalar(
            select(DocumentJob).where(
                DocumentJob.owner_subject == owner,
                DocumentJob.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return _response(existing)
    data = bytearray()
    try:
        while True:
            chunk = await document.read(1024 * 1024)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > settings.document_max_upload_bytes:
                return _error(
                    request, "DOCUMENT_TOO_LARGE", "Documents must be 10 MB or smaller", 413
                )
        service = DocumentExtractionService(settings=settings)
        document_format = service.detect_format(
            bytes(data), document.filename or "document", document.content_type
        )
        key = PrivateDocumentStorage(settings.document_storage_root).key(document_format)
        storage = PrivateDocumentStorage(settings.document_storage_root)
        storage.write(key, bytes(data))
        job = DocumentJob(
            owner_subject=owner,
            idempotency_key=idempotency_key,
            original_filename=Path(document.filename or "document").name[:255],
            content_type=document.content_type or "application/octet-stream",
            document_format=document_format,
            source_language=source_language.strip() if source_language else None,
            storage_key=key,
            size_bytes=len(data),
            expires_at=expiration(settings),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        try:
            task_id = enqueue_document_extraction(job.id)
        except RuntimeError:
            job.status = "failed"
            job.error_code = "DOCUMENT_QUEUE_UNAVAILABLE"
            job.error_message = "Document processing is temporarily unavailable"
            storage.delete(key)
            await db.commit()
            return _error(
                request,
                "DOCUMENT_QUEUE_UNAVAILABLE",
                "Document processing is temporarily unavailable",
                503,
            )
        job.celery_task_id = task_id
        await db.commit()
        return _response(job)
    except DocumentExtractionError as error:
        return _error(request, error.code, error.message, error.status_code)
    finally:
        await document.close()


@router.get("/{job_id}", response_model=DocumentJobResponse)
async def get_job(
    job_id: str, owner: str = Depends(require_document_owner), db: AsyncSession = Depends(get_db)
) -> DocumentJobResponse:
    return _response(await _owned(job_id, owner, db))


@router.get("/{job_id}/segments", response_model=DocumentSegmentsResponse)
async def get_segments(
    job_id: str, owner: str = Depends(require_document_owner), db: AsyncSession = Depends(get_db)
) -> DocumentSegmentsResponse:
    job = await _owned(job_id, owner, db)
    return DocumentSegmentsResponse(
        job_id=job.id,
        status=job.status,
        segments=normalize_document_segments(job.segments),
    )


@router.put("/{job_id}/segments", response_model=DocumentSegmentsResponse)
async def update_segments(
    job_id: str,
    payload: DocumentSegmentsUpdate,
    owner: str = Depends(require_document_owner),
    db: AsyncSession = Depends(get_db),
) -> DocumentSegmentsResponse:
    job = await _owned(job_id, owner, db)
    settings = get_settings()
    if job.status != "awaiting_review":
        raise DocumentExtractionError(
            "DOCUMENT_NOT_REVIEWABLE",
            "Document segments are not available for review",
            status_code=409,
        )
    if any(
        len(segment.source_text) > settings.document_max_segment_characters
        for segment in payload.segments
    ):
        raise DocumentExtractionError(
            "SEGMENT_TOO_LARGE", "Each segment exceeds the character limit", status_code=422
        )
    job.segments = [segment.model_dump() for segment in payload.segments]
    await db.commit()
    return DocumentSegmentsResponse.model_validate(
        {"job_id": job.id, "status": job.status, "segments": job.segments}
    )


@router.post("/{job_id}/translate", response_model=DocumentJobResponse, status_code=202)
async def translate_job(
    job_id: str,
    payload: DocumentTranslationRequest,
    request: Request,
    owner: str = Depends(require_document_owner),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> DocumentJobResponse:
    job = await _owned(job_id, owner, db)
    if job.status not in {"awaiting_review", "failed"}:
        raise DocumentExtractionError(
            "DOCUMENT_NOT_TRANSLATABLE",
            "Document is not ready for translation",
            status_code=409,
        )
    if not payload.reviewed:
        raise DocumentExtractionError(
            "DOCUMENT_REVIEW_REQUIRED",
            "Review the extracted text before translating",
            status_code=409,
        )
    registry = get_translation_registry()
    if registry.get_for("text_translation") is None:
        raise DocumentExtractionError(
            "TRANSLATION_ENGINE_NOT_CONFIGURED", "Translation is not configured", status_code=503
        )
    if payload.target_language not in SUPPORTED_LANGUAGE_CODES or (
        payload.source_language and payload.source_language not in SUPPORTED_LANGUAGE_CODES
    ):
        raise DocumentExtractionError(
            "UNSUPPORTED_LANGUAGE", "The selected language is not supported", status_code=422
        )
    if payload.source_language == payload.target_language:
        raise DocumentExtractionError(
            "INVALID_LANGUAGE_PAIR",
            "Source and target languages must be different",
            status_code=422,
        )
    key = (idempotency_key or "").strip()[:128] or None
    if job.translation_idempotency_key and job.translation_idempotency_key == key:
        return _response(job)
    job.source_language = payload.source_language
    job.target_language = payload.target_language
    job.translation_idempotency_key = key
    job.status = "translating"
    job.progress = 1
    await db.commit()
    try:
        job.translation_task_id = enqueue_document_translation(job.id)
        await db.commit()
    except RuntimeError:
        job.status = "awaiting_review"
        job.error_code = "DOCUMENT_QUEUE_UNAVAILABLE"
        job.error_message = "Document processing is temporarily unavailable"
        await db.commit()
        raise DocumentExtractionError(
            "DOCUMENT_QUEUE_UNAVAILABLE",
            "Document processing is temporarily unavailable",
            status_code=503,
        )
    return _response(job)


@router.get("/{job_id}/download")
async def download_job(
    job_id: str,
    request: Request,
    owner: str = Depends(require_document_owner),
    db: AsyncSession = Depends(get_db),
):
    job = await _owned(job_id, owner, db)
    if job.status != "completed" or not job.output_storage_key:
        raise DocumentExtractionError(
            "DOCUMENT_OUTPUT_UNAVAILABLE", "The translated document is not ready", status_code=409
        )
    storage = PrivateDocumentStorage(get_settings().document_storage_root)
    if not storage.exists(job.output_storage_key):
        raise DocumentExtractionError(
            "DOCUMENT_OUTPUT_UNAVAILABLE",
            "The translated document is no longer available",
            status_code=404,
        )
    filename = job.output_filename or "translated-document.txt"
    safe_name = filename.replace('"', "").replace("\\", "")
    return FileResponse(
        storage._path(job.output_storage_key),  # private, validated storage key
        media_type=job.output_content_type or "application/octet-stream",
        filename=safe_name,
        headers={"X-Request-ID": request.state.request_id},
    )


@router.post("/{job_id}/cancel", response_model=DocumentJobResponse)
async def cancel_job(
    job_id: str, owner: str = Depends(require_document_owner), db: AsyncSession = Depends(get_db)
) -> DocumentJobResponse:
    job = await _owned(job_id, owner, db)
    if job.status in {"queued", "extracting", "translating", "exporting"}:
        job.status = "cancelled"
        await db.commit()
    return _response(job)


@router.post("/{job_id}/retry", response_model=DocumentJobResponse)
async def retry_job(
    job_id: str, owner: str = Depends(require_document_owner), db: AsyncSession = Depends(get_db)
) -> DocumentJobResponse:
    job = await _owned(job_id, owner, db)
    settings = get_settings()
    if job.status != "failed" or job.attempt_count >= settings.document_job_max_attempts:
        raise DocumentExtractionError(
            "DOCUMENT_RETRY_UNAVAILABLE", "This document cannot be retried", status_code=409
        )
    job.status = "translating" if job.target_language else "queued"
    job.error_code = None
    job.error_message = None
    await db.commit()
    try:
        if job.target_language:
            job.translation_task_id = enqueue_document_translation(job.id)
        else:
            job.celery_task_id = enqueue_document_extraction(job.id)
        await db.commit()
    except RuntimeError:
        raise DocumentExtractionError(
            "DOCUMENT_QUEUE_UNAVAILABLE",
            "Document processing is temporarily unavailable",
            status_code=503,
        )
    return _response(job)


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: str, owner: str = Depends(require_document_owner), db: AsyncSession = Depends(get_db)
) -> None:
    job = await _owned(job_id, owner, db)
    PrivateDocumentStorage(get_settings().document_storage_root).delete(job.storage_key)
    if job.output_storage_key:
        PrivateDocumentStorage(get_settings().document_storage_root).delete(job.output_storage_key)
    await db.execute(
        delete(DocumentJob).where(DocumentJob.id == job.id, DocumentJob.owner_subject == owner)
    )
    await db.commit()
