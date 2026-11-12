from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import error_payload
from app.providers.documents.base import DocumentExtractionError


async def document_error_handler(request: Request, exc: DocumentExtractionError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, request_id=request.state.request_id),
    )
