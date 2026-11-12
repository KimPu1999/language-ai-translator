from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.errors import error_payload
from app.db.session import check_db

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(request: Request):
    try:
        await check_db()
    except Exception:
        return JSONResponse(
            status_code=503,
            content=error_payload(
                "DATABASE_UNAVAILABLE",
                "Database unavailable",
                request_id=request.state.request_id,
            ),
        )
    return {"status": "ready"}
