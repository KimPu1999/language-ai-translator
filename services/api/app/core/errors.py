from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_payload(
    code: str,
    message: str,
    details: Any = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    if request_id is not None:
        payload["error"]["request_id"] = request_id
    return payload


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {key: value for key, value in error.items() if key not in {"input", "ctx"}}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "VALIDATION_ERROR",
            "Request validation failed",
            details,
            request_id=request.state.request_id,
        ),
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    del exc
    return JSONResponse(
        status_code=503,
        content=error_payload(
            "DATABASE_UNAVAILABLE", "Database unavailable", request_id=request.state.request_id
        ),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = {**exc.detail, "error": {**exc.detail["error"]}}
        content["error"]["request_id"] = request.state.request_id
    else:
        content = error_payload(
            f"HTTP_{exc.status_code}",
            str(exc.detail),
            request_id=request.state.request_id,
        )
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)
