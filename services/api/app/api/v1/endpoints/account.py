from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import current_auth_context
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.account import (
    AccountDeletionRequest,
    AccountMessageResponse,
    FavoriteCreateRequest,
    FavoriteItem,
    FavoriteListResponse,
    HistoryCreateRequest,
    HistoryItem,
    HistoryListResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.account import (
    AccountService,
    FavoriteService,
    HistoryService,
    PreferenceService,
    ProfileService,
)
from app.services.auth import AuthContext, clear_auth_cookies

router = APIRouter(tags=["account"])


@router.get("/api/v1/profile", response_model=ProfileResponse)
async def get_profile(
    context: AuthContext = Depends(current_auth_context), db: AsyncSession = Depends(get_db)
) -> ProfileResponse:
    return await ProfileService(db).get(context)


@router.patch("/api/v1/profile", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    return await ProfileService(db).update(context, payload)


@router.get("/api/v1/preferences", response_model=PreferencesResponse)
async def get_preferences(
    context: AuthContext = Depends(current_auth_context), db: AsyncSession = Depends(get_db)
) -> PreferencesResponse:
    return await PreferenceService(db).get(context)


@router.patch("/api/v1/preferences", response_model=PreferencesResponse)
async def update_preferences(
    payload: PreferencesUpdateRequest,
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> PreferencesResponse:
    return await PreferenceService(db).update(context, payload)


@router.get("/api/v1/history", response_model=HistoryListResponse)
async def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source_language: str | None = Query(default=None, min_length=2, max_length=32),
    target_language: str | None = Query(default=None, min_length=2, max_length=32),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> HistoryListResponse:
    return await HistoryService(db).list(
        context,
        limit=limit,
        offset=offset,
        source_language=source_language,
        target_language=target_language,
        query=q,
    )


@router.post("/api/v1/history", response_model=HistoryItem, status_code=201)
async def save_history(
    payload: HistoryCreateRequest,
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> HistoryItem:
    return await HistoryService(db).create(context, payload)


@router.delete("/api/v1/history/{translation_id}", status_code=204)
async def delete_history(
    translation_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    await HistoryService(db).delete(context, translation_id)


@router.delete("/api/v1/history", status_code=204)
async def clear_history(
    context: AuthContext = Depends(current_auth_context), db: AsyncSession = Depends(get_db)
) -> None:
    await HistoryService(db).clear(context)


@router.get("/api/v1/favorites", response_model=FavoriteListResponse)
async def list_favorites(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> FavoriteListResponse:
    return await FavoriteService(db).list(context, limit=limit, offset=offset)


@router.post("/api/v1/favorites", response_model=FavoriteItem, status_code=201)
async def create_favorite(
    payload: FavoriteCreateRequest,
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> FavoriteItem:
    return await FavoriteService(db).create(context, payload.translation_id)


@router.delete("/api/v1/favorites/{favorite_id}", status_code=204)
async def delete_favorite(
    favorite_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    await FavoriteService(db).delete(context, favorite_id)


@router.get("/api/v1/account/export")
async def export_account(
    request: Request,
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    data = await AccountService(
        db, storage_root=get_settings().document_storage_root
    ).export(context)
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": 'attachment; filename="lingua-account-export.json"',
            "X-Request-ID": request.state.request_id,
        },
    )


@router.delete("/api/v1/account", response_model=AccountMessageResponse)
async def delete_account(
    payload: AccountDeletionRequest,
    response: Response,
    context: AuthContext = Depends(current_auth_context),
    db: AsyncSession = Depends(get_db),
) -> AccountMessageResponse:
    await AccountService(
        db, storage_root=get_settings().document_storage_root
    ).delete_account(context, payload.password)
    clear_auth_cookies(response, get_settings())
    return AccountMessageResponse(message="Account deleted")
