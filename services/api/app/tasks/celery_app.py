from __future__ import annotations

from app.core.config import get_settings

try:
    from celery import Celery

    settings = get_settings()
    celery_app = Celery(
        "lingua_api",
        broker=settings.redis_url or "",
        backend=settings.redis_url or "",
        include=["app.tasks.document_tasks"],
    )
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_track_started=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        beat_schedule={
            "cleanup-expired-document-jobs": {
                "task": "app.tasks.document_tasks.cleanup_expired_document_jobs",
                "schedule": 3600.0,
            }
        },
    )
    CELERY_AVAILABLE = True
except ImportError:
    celery_app = None
    CELERY_AVAILABLE = False
