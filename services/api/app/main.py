from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints import health, languages, translations
from app.core.config import get_settings
from app.core.errors import (
    database_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.include_router(health.router)
app.include_router(languages.router)
app.include_router(translations.router)
