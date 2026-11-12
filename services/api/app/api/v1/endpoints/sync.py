# ruff: noqa: E501
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import current_auth_context
from app.db.session import get_db
from app.schemas.sync import (
    SyncChangesResponse,
    SyncConsentRequest,
    SyncImportRequest,
    SyncImportResponse,
    SyncPreferencesRequest,
    SyncPreviewRequest,
    SyncPreviewResponse,
    SyncStatusResponse,
)
from app.services.auth import AuthContext
from app.services.sync import SyncService

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.get("/status", response_model=SyncStatusResponse)
async def sync_status(context: AuthContext = Depends(current_auth_context), db: AsyncSession = Depends(get_db)) -> SyncStatusResponse:
    return await SyncService(db).status(context)


@router.patch("/consent", response_model=SyncStatusResponse)
async def sync_consent(payload: SyncConsentRequest, context: AuthContext = Depends(current_auth_context), db: AsyncSession = Depends(get_db)) -> SyncStatusResponse:
    return await SyncService(db).set_consent(context, payload)


@router.patch("/preferences", response_model=SyncStatusResponse)
async def sync_preferences(payload: SyncPreferencesRequest, context: AuthContext = Depends(current_auth_context), db: AsyncSession = Depends(get_db)) -> SyncStatusResponse:
    return await SyncService(db).update_preferences(context, payload)


@router.post("/preview", response_model=SyncPreviewResponse)
async def sync_preview(payload: SyncPreviewRequest, context: AuthContext = Depends(current_auth_context), db: AsyncSession = Depends(get_db)) -> SyncPreviewResponse:
    return await SyncService(db).preview(context, payload)


@router.post("/import", response_model=SyncImportResponse)
async def sync_import(payload: SyncImportRequest, context: AuthContext = Depends(current_auth_context), db: AsyncSession = Depends(get_db)) -> SyncImportResponse:
    return await SyncService(db).import_records(context, payload)


@router.get("/changes", response_model=SyncChangesResponse)
async def sync_changes(
    request: Request,
    cursor: str | None = Query(default=None, max_length=512),
    limit: int = Query(default=50, ge=1, le=100),
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> SyncChangesResponse:
    del request
    return await SyncService(db).changes(context, cursor, limit)
