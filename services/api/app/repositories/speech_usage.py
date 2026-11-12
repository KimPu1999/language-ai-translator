from sqlalchemy.ext.asyncio import AsyncSession

from app.models.speech_usage_event import SpeechUsageEvent


async def record_speech_usage_event(
    session: AsyncSession,
    *,
    request_id: str,
    operation: str,
    provider: str,
    locale: str,
    voice: str | None,
    input_bytes: int,
    duration_ms: int | None,
    character_count: int,
    status: str,
    latency_ms: int,
    error_code: str | None = None,
) -> None:
    """Persist only speech operation metadata; never audio or transcript content."""
    session.add(
        SpeechUsageEvent(
            request_id=request_id,
            operation=operation,
            provider=provider,
            locale=locale,
            voice=voice,
            input_bytes=input_bytes,
            duration_ms=duration_ms,
            character_count=character_count,
            status=status,
            latency_ms=latency_ms,
            error_code=error_code,
        )
    )
    try:
        await session.commit()
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
