from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.text import character_count
from app.db.session import SessionLocal
from app.models.document_job import DocumentJob
from app.models.document_usage_event import DocumentUsageEvent
from app.providers.documents.base import DocumentExtractionError
from app.providers.ocr.registry import get_ocr_registry
from app.providers.translation.base import TranslationProviderError
from app.providers.translation.registry import get_translation_registry
from app.services.detection import LanguageDetectionService
from app.services.document_export import exporter_for, safe_output_filename
from app.services.document_storage import PrivateDocumentStorage
from app.services.documents import (
    DocumentExtractionService,
    normalize_document_segments,
    segment_document_blocks,
)
from app.services.translation import TranslationService
from app.tasks.celery_app import CELERY_AVAILABLE, celery_app


async def _process(job_id: UUID) -> None:
    settings = get_settings()
    storage = PrivateDocumentStorage(settings.document_storage_root)
    started = time.perf_counter()
    async with SessionLocal() as session:
        job = await session.get(DocumentJob, job_id, with_for_update=True)
        if job is None or job.status in {"cancelled", "expired", "completed", "awaiting_review"}:
            return
        if job.expires_at <= datetime.now(UTC):
            job.status = "expired"
            storage.delete(job.storage_key)
            if job.output_storage_key:
                storage.delete(job.output_storage_key)
            await session.commit()
            return
        if job.status != "queued":
            return
        job.status = "extracting"
        job.progress = 10
        job.attempt_count += 1
        await session.commit()

        try:
            data = storage.read(job.storage_key)
            registry = get_ocr_registry()
            result = await asyncio.to_thread(
                DocumentExtractionService(ocr_registry=registry, settings=settings).extract,
                data,
                filename=job.original_filename,
                content_type=job.content_type,
                source_language=job.source_language,
            )
            await session.refresh(job)
            if job.status == "cancelled":
                storage.delete(job.storage_key)
                await session.commit()
                return
            job.segments = list(
                segment_document_blocks(
                    result.blocks, limit=settings.document_max_segment_characters
                )
            )
            job.page_count = result.pages
            job.ocr_pages = list(result.ocr_pages)
            job.progress = 100
            job.status = "awaiting_review"
            await session.commit()
            session.add(
                DocumentUsageEvent(
                    job_id=job.id,
                    owner_subject=job.owner_subject,
                    document_format=job.document_format,
                    file_size=job.size_bytes,
                    status="success",
                    execution_ms=int((time.perf_counter() - started) * 1000),
                )
            )
            await session.commit()
        except DocumentExtractionError as error:
            job.status = "failed"
            job.error_code = error.code
            job.error_message = error.message
            await session.commit()
            session.add(
                DocumentUsageEvent(
                    job_id=job.id,
                    owner_subject=job.owner_subject,
                    document_format=job.document_format,
                    file_size=job.size_bytes,
                    status="failed",
                    error_code=error.code,
                    execution_ms=int((time.perf_counter() - started) * 1000),
                )
            )
            await session.commit()
        except Exception:
            # Keep an unexpected parser/provider failure from leaving the job
            # permanently stuck in `extracting`. The public error is stable
            # and deliberately contains no document/provider details.
            job.status = "failed"
            job.error_code = "DOCUMENT_PROCESSING_FAILED"
            job.error_message = "The document could not be processed"
            await session.commit()
            session.add(
                DocumentUsageEvent(
                    job_id=job.id,
                    owner_subject=job.owner_subject,
                    document_format=job.document_format,
                    file_size=job.size_bytes,
                    status="failed",
                    error_code="DOCUMENT_PROCESSING_FAILED",
                    execution_ms=int((time.perf_counter() - started) * 1000),
                )
            )
            await session.commit()


async def _cleanup() -> None:
    settings = get_settings()
    storage = PrivateDocumentStorage(settings.document_storage_root)
    async with SessionLocal() as session:
        result = await session.execute(
            select(DocumentJob).where(
                DocumentJob.expires_at <= datetime.now(UTC),
                DocumentJob.status != "expired",
            )
        )
        jobs = list(result.scalars())
        for job in jobs:
            if job.status != "cancelled":
                job.status = "expired"
            storage.delete(job.storage_key)
            if job.output_storage_key:
                storage.delete(job.output_storage_key)
        if jobs:
            await session.commit()


async def _translate_and_export(job_id: UUID) -> None:
    settings = get_settings()
    storage = PrivateDocumentStorage(settings.document_storage_root)
    started = time.perf_counter()
    async with SessionLocal() as session:
        job = await session.get(DocumentJob, job_id, with_for_update=True)
        if job is None or job.status in {"cancelled", "expired", "completed"}:
            return
        if job.expires_at <= datetime.now(UTC):
            job.status = "expired"
            storage.delete(job.storage_key)
            if job.output_storage_key:
                storage.delete(job.output_storage_key)
            await session.commit()
            return
        job.status = "translating"
        job.progress = max(job.progress, 1)
        job.error_code = None
        job.error_message = None
        await session.commit()
        registry = get_translation_registry()
        service = TranslationService(registry)
        segments = normalize_document_segments(job.segments)
        try:
            source_language = job.source_language
            if not source_language:
                detection_text = "\n".join(item.get("source_text", "") for item in segments)
                source_language = (
                    await LanguageDetectionService(registry).detect(text=detection_text)
                ).language
                job.source_language = source_language
            total = len(segments) or 1
            for index, segment in enumerate(segments):
                await session.refresh(job)
                if job.status == "cancelled":
                    await session.commit()
                    return
                if segment.get("translated_text"):
                    continue
                source_text = str(segment.get("source_text", ""))
                result = await service.translate(
                    source_language=source_language,
                    target_language=job.target_language or "",
                    text=source_text,
                )
                segment["translated_text"] = result.translated_text
                segment["provider"] = result.provider
                job.segments = segments
                job.translation_provider = result.provider
                job.translation_characters += character_count(source_text)
                job.progress = min(95, 5 + int(((index + 1) / total) * 90))
                await session.commit()
            job.status = "exporting"
            job.progress = 96
            await session.commit()
            exported = exporter_for(job.document_format).export(
                title=job.original_filename, segments=segments
            )
            exporter = exporter_for(job.document_format)
            output_key = storage.key(exporter.extension)
            storage.write(output_key, exported)
            job.output_storage_key = output_key
            job.output_content_type = exporter.content_type
            job.output_filename = safe_output_filename(job.original_filename, exporter.extension)
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(UTC)
            await session.commit()
            session.add(DocumentUsageEvent(
                job_id=job.id, owner_subject=job.owner_subject, document_format=job.document_format,
                file_size=job.size_bytes, status="success", operation="translation",
                provider=job.translation_provider, characters=job.translation_characters,
                execution_ms=int((time.perf_counter() - started) * 1000),
            ))
            await session.commit()
        except TranslationProviderError as error:
            job.status = "failed"
            job.error_code = error.code
            job.error_message = error.message
            await session.commit()
            session.add(DocumentUsageEvent(
                job_id=job.id, owner_subject=job.owner_subject, document_format=job.document_format,
                file_size=job.size_bytes, status="failed", operation="translation",
                provider=job.translation_provider, characters=job.translation_characters,
                error_code=error.code, execution_ms=int((time.perf_counter() - started) * 1000),
            ))
            await session.commit()
        except Exception:
            job.status = "failed"
            job.error_code = "DOCUMENT_EXPORT_FAILED"
            job.error_message = "The translated document could not be exported"
            await session.commit()



if CELERY_AVAILABLE:

    @celery_app.task(
        bind=True,
        name="app.tasks.document_tasks.extract_document",
        max_retries=2,
        soft_time_limit=get_settings().document_job_time_limit_seconds,
        time_limit=get_settings().document_job_time_limit_seconds + 15,
    )
    def extract_document(self, job_id: str):
        try:
            asyncio.run(_process(UUID(job_id)))
        except Exception as exc:
            raise extract_document.retry(exc=exc, countdown=10)

    @celery_app.task(name="app.tasks.document_tasks.cleanup_expired_document_jobs")
    def cleanup_expired_document_jobs():
        asyncio.run(_cleanup())

else:

    class _UnavailableTask:
        def delay(self, *_args, **_kwargs):
            raise RuntimeError("Celery is not installed")

        def apply_async(self, *_args, **_kwargs):
            raise RuntimeError("Celery is not installed")

    extract_document = _UnavailableTask()
    cleanup_expired_document_jobs = _UnavailableTask()
    class _UnavailableTranslationTask(_UnavailableTask):
        pass
    translate_document = _UnavailableTranslationTask()


def enqueue_document_extraction(job_id: UUID) -> str:
    if not CELERY_AVAILABLE or not get_settings().redis_url:
        raise RuntimeError("Document job queue is unavailable")
    result = extract_document.delay(str(job_id))
    return str(result.id)


if CELERY_AVAILABLE:

    @celery_app.task(
        bind=True,
        name="app.tasks.document_tasks.translate_document",
        max_retries=2,
        soft_time_limit=get_settings().document_job_time_limit_seconds,
        time_limit=get_settings().document_job_time_limit_seconds + 15,
    )
    def translate_document(self, job_id: str):
        try:
            asyncio.run(_translate_and_export(UUID(job_id)))
        except Exception as exc:
            raise translate_document.retry(exc=exc, countdown=10)


def enqueue_document_translation(job_id: UUID) -> str:
    if not CELERY_AVAILABLE or not get_settings().redis_url:
        raise RuntimeError("Document job queue is unavailable")
    result = translate_document.delay(str(job_id))
    return str(result.id)
