from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints import (
    account,
    auth,
    document_jobs,
    documents,
    health,
    languages,
    ocr,
    speech,
    sync,
    translations,
    voice,
)
from app.core.account_errors import AccountDataError
from app.core.auth_errors import AuthenticationError
from app.core.config import get_settings
from app.core.document_errors import document_error_handler
from app.core.errors import (
    account_data_exception_handler,
    authentication_exception_handler,
    database_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.providers.documents.base import DocumentExtractionError

settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")


@app.middleware("http")
async def request_id_middleware(request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(DocumentExtractionError, document_error_handler)
app.add_exception_handler(AuthenticationError, authentication_exception_handler)
app.add_exception_handler(AccountDataError, account_data_exception_handler)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(languages.router)
app.include_router(translations.router)
app.include_router(speech.router)
app.include_router(sync.router)
app.include_router(voice.router)
app.include_router(ocr.router)
app.include_router(documents.router)
app.include_router(document_jobs.router)
