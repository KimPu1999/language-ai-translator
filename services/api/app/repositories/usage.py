from sqlalchemy.ext.asyncio import AsyncSession

from app.models.translation_usage_event import TranslationUsageEvent


async def record_usage_event(
    session: AsyncSession,
    *,
    request_id: str,
    operation: str,
    provider: str,
    source_language: str | None,
    target_language: str | None,
    character_count: int,
    status: str,
    latency_ms: int,
    error_code: str | None = None,
) -> None:
    """Persist metadata only; raw source and translated text never enter this record."""
    session.add(
        TranslationUsageEvent(
            request_id=request_id,
            operation=operation,
            provider=provider,
            source_language=source_language,
            target_language=target_language,
            character_count=character_count,
            status=status,
            latency_ms=latency_ms,
            error_code=error_code,
        )
    )
    try:
        await session.commit()
    except Exception:
        # Usage telemetry must never turn a translation response into a database error.
        try:
            await session.rollback()
        except Exception:
            pass
