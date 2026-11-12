from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr_usage_event import OCRUsageEvent


async def record_ocr_usage_event(
    session: AsyncSession,
    *,
    request_id: str,
    provider: str,
    language: str,
    width: int | None,
    height: int | None,
    file_size: int,
    execution_ms: int,
    status: str,
    error_code: str | None = None,
    billable_units: int = 0,
) -> None:
    """Persist OCR metadata only; never image bytes or extracted text."""
    session.add(
        OCRUsageEvent(
            request_id=request_id,
            provider=provider,
            language=language,
            width=width,
            height=height,
            file_size=file_size,
            execution_ms=execution_ms,
            status=status,
            error_code=error_code,
            billable_units=billable_units,
        )
    )
    try:
        await session.commit()
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
