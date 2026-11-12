from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from pwdlib import PasswordHash
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.account_errors import AccountDataError
from app.models.auth_action_token import AuthActionToken
from app.models.auth_session import AuthSession
from app.models.document_job import DocumentJob
from app.models.favorite import Favorite
from app.models.sync_record import SyncRecord
from app.models.translation import Translation
from app.models.user import User
from app.models.user_preference import UserPreference
from app.providers.translation.azure import SUPPORTED_LANGUAGE_CODES
from app.schemas.account import (
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
from app.services.auth import AuthContext
from app.services.document_storage import PrivateDocumentStorage

PASSWORD_HASHER = PasswordHash.recommended()
DEFAULT_LOCALE = "en"
DEFAULT_THEME = "system"


def _now() -> datetime:
    return datetime.now(UTC)


def _profile(user: User) -> ProfileResponse:
    if not user.email:
        raise AccountDataError("ACCOUNT_UNAVAILABLE", "Account is unavailable", status_code=503)
    return ProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
    )


def _preferences(preference: UserPreference | None) -> PreferencesResponse:
    return PreferencesResponse(
        locale=preference.locale if preference else DEFAULT_LOCALE,
        theme=preference.theme if preference else DEFAULT_THEME,
        history_enabled=preference.history_enabled if preference else False,
        sync_enabled=preference.sync_enabled if preference else False,
    )


def _translation_item(translation: Translation) -> HistoryItem:
    return HistoryItem(
        id=translation.id,
        source_language=translation.source_language_code,
        target_language=translation.target_language_code,
        source_text=translation.source_text,
        translated_text=translation.translated_text,
        provider=translation.provider,
        created_at=translation.created_at,
    )


def _validate_languages(source: str, target: str) -> None:
    if source not in SUPPORTED_LANGUAGE_CODES or target not in SUPPORTED_LANGUAGE_CODES:
        raise AccountDataError(
            "UNSUPPORTED_LANGUAGE", "The selected language is not supported", status_code=422
        )
    if source == target:
        raise AccountDataError(
            "INVALID_LANGUAGE_PAIR",
            "Source and target languages must be different",
            status_code=422,
        )


async def _mark_sync_deleted(
    db: AsyncSession, user_id, *, entity_type: str, server_record_id=None
) -> None:
    filters = [SyncRecord.user_id == user_id, SyncRecord.entity_type == entity_type]
    if server_record_id is not None:
        filters.append(SyncRecord.server_record_id == server_record_id)
    records = await db.scalars(select(SyncRecord).where(and_(*filters)))
    now = _now()
    for record in records:
        record.version += 1
        record.client_updated_at = now
        record.deleted_at = now
        record.updated_at = now
        record.payload = {}
        record.payload_hash = hashlib.sha256(b"").hexdigest()
class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, context: AuthContext) -> ProfileResponse:
        return _profile(context.user)

    async def update(
        self, context: AuthContext, payload: ProfileUpdateRequest
    ) -> ProfileResponse:
        if "display_name" in payload.model_fields_set:
            context.user.display_name = payload.display_name
        await self.db.commit()
        return _profile(context.user)


class PreferenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, context: AuthContext) -> PreferencesResponse:
        preference = await self.db.get(UserPreference, context.user.id)
        return _preferences(preference)

    async def update(
        self, context: AuthContext, payload: PreferencesUpdateRequest
    ) -> PreferencesResponse:
        preference = await self.db.get(UserPreference, context.user.id)
        if preference is None:
            preference = UserPreference(user_id=context.user.id)
            self.db.add(preference)
        if payload.locale is not None:
            preference.locale = payload.locale
        if payload.theme is not None:
            preference.theme = payload.theme
        if payload.history_enabled is not None:
            preference.history_enabled = payload.history_enabled
        if payload.sync_enabled is not None:
            preference.sync_enabled = payload.sync_enabled
        await self.db.commit()
        return _preferences(preference)


class HistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _require_opt_in(self, user_id) -> None:
        preference = await self.db.get(UserPreference, user_id)
        if not preference or not preference.history_enabled:
            raise AccountDataError(
                "HISTORY_OPT_IN_REQUIRED",
                "Enable history in preferences before saving translations",
                status_code=403,
            )

    async def create(
        self, context: AuthContext, payload: HistoryCreateRequest
    ) -> HistoryItem:
        await self._require_opt_in(context.user.id)
        _validate_languages(payload.source_language, payload.target_language)
        translation = Translation(
            user_id=context.user.id,
            source_language_code=payload.source_language,
            target_language_code=payload.target_language,
            source_text=payload.source_text,
            translated_text=payload.translated_text,
            provider=payload.provider,
            created_at=_now(),
        )
        self.db.add(translation)
        await self.db.flush()
        await self.db.commit()
        return _translation_item(translation)

    async def list(
        self,
        context: AuthContext,
        *,
        limit: int,
        offset: int,
        source_language: str | None,
        target_language: str | None,
        query: str | None,
    ) -> HistoryListResponse:
        filters = [Translation.user_id == context.user.id]
        if source_language:
            filters.append(Translation.source_language_code == source_language)
        if target_language:
            filters.append(Translation.target_language_code == target_language)
        if query:
            pattern = f"%{query}%"
            filters.append(
                or_(
                    Translation.source_text.ilike(pattern),
                    Translation.translated_text.ilike(pattern),
                )
            )
        where = and_(*filters)
        total = await self.db.scalar(select(func.count()).select_from(Translation).where(where))
        result = await self.db.scalars(
            select(Translation)
            .where(where)
            .order_by(Translation.created_at.desc(), Translation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return HistoryListResponse(
            items=[_translation_item(item) for item in result],
            total=int(total or 0),
            limit=limit,
            offset=offset,
        )

    async def delete(self, context: AuthContext, translation_id) -> None:
        await _mark_sync_deleted(
            self.db,
            context.user.id,
            entity_type="translation",
            server_record_id=translation_id,
        )
        result = await self.db.execute(
            delete(Translation).where(
                Translation.id == translation_id, Translation.user_id == context.user.id
            )
        )
        if not result.rowcount:
            raise AccountDataError("HISTORY_NOT_FOUND", "History item not found", status_code=404)
        await self.db.commit()

    async def clear(self, context: AuthContext) -> None:
        await _mark_sync_deleted(self.db, context.user.id, entity_type="translation")
        await _mark_sync_deleted(self.db, context.user.id, entity_type="favorite")
        await self.db.execute(delete(Favorite).where(Favorite.user_id == context.user.id))
        await self.db.execute(delete(Translation).where(Translation.user_id == context.user.id))
        await self.db.commit()


class FavoriteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _item(favorite: Favorite, translation: Translation) -> FavoriteItem:
        return FavoriteItem(
            id=favorite.id,
            translation_id=favorite.translation_id,
            created_at=favorite.created_at,
            translation=_translation_item(translation),
        )

    async def create(self, context: AuthContext, translation_id) -> FavoriteItem:
        translation = await self.db.scalar(
            select(Translation).where(
                Translation.id == translation_id, Translation.user_id == context.user.id
            )
        )
        if translation is None:
            raise AccountDataError(
                "TRANSLATION_NOT_FOUND", "Translation not found", status_code=404
            )
        favorite = await self.db.scalar(
            select(Favorite).where(
                Favorite.user_id == context.user.id,
                Favorite.translation_id == translation_id,
            )
        )
        if favorite is None:
            favorite = Favorite(
                user_id=context.user.id,
                translation_id=translation_id,
                created_at=_now(),
            )
            self.db.add(favorite)
            try:
                await self.db.flush()
                await self.db.commit()
            except IntegrityError as exc:
                await self.db.rollback()
                raise AccountDataError(
                    "FAVORITE_CONFLICT", "Favorite could not be created", status_code=409
                ) from exc
        return self._item(favorite, translation)

    async def list(
        self, context: AuthContext, *, limit: int, offset: int
    ) -> FavoriteListResponse:
        where = Favorite.user_id == context.user.id
        total = await self.db.scalar(select(func.count()).select_from(Favorite).where(where))
        result = await self.db.execute(
            select(Favorite, Translation)
            .join(Translation, Translation.id == Favorite.translation_id)
            .where(where)
            .order_by(Favorite.created_at.desc(), Favorite.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return FavoriteListResponse(
            items=[self._item(favorite, translation) for favorite, translation in result.all()],
            total=int(total or 0),
            limit=limit,
            offset=offset,
        )

    async def delete(self, context: AuthContext, favorite_id) -> None:
        await _mark_sync_deleted(
            self.db,
            context.user.id,
            entity_type="favorite",
            server_record_id=favorite_id,
        )
        result = await self.db.execute(
            delete(Favorite).where(
                Favorite.id == favorite_id, Favorite.user_id == context.user.id
            )
        )
        if not result.rowcount:
            raise AccountDataError("FAVORITE_NOT_FOUND", "Favorite not found", status_code=404)
        await self.db.commit()


class AccountService:
    def __init__(self, db: AsyncSession, *, storage_root: str) -> None:
        self.db = db
        self.storage_root = storage_root

    async def export(self, context: AuthContext) -> dict[str, Any]:
        preference = await self.db.get(UserPreference, context.user.id)
        translations = await self.db.scalars(
            select(Translation)
            .where(Translation.user_id == context.user.id)
            .order_by(Translation.created_at.asc(), Translation.id.asc())
        )
        favorites = await self.db.execute(
            select(Favorite, Translation)
            .join(Translation, Translation.id == Favorite.translation_id)
            .where(Favorite.user_id == context.user.id)
            .order_by(Favorite.created_at.asc(), Favorite.id.asc())
        )
        jobs = await self.db.scalars(
            select(DocumentJob)
            .where(DocumentJob.owner_subject == f"user:{context.user.id}")
            .order_by(DocumentJob.created_at.asc(), DocumentJob.id.asc())
        )
        return {
            "export_version": 1,
            "exported_at": _now().isoformat(),
            "account": {
                "id": str(context.user.id),
                "email": context.user.email,
                "display_name": context.user.display_name,
                "email_verified": context.user.email_verified_at is not None,
                "created_at": context.user.created_at.isoformat(),
            },
            "preferences": _preferences(preference).model_dump(),
            "history": [
                _translation_item(item).model_dump(mode="json") for item in translations
            ],
            "favorites": [
                {
                    "id": str(favorite.id),
                    "translation_id": str(favorite.translation_id),
                    "created_at": favorite.created_at.isoformat(),
                    "translation": _translation_item(translation).model_dump(mode="json"),
                }
                for favorite, translation in favorites.all()
            ],
            "documents": [
                {
                    "id": str(job.id),
                    "filename": job.original_filename,
                    "format": job.document_format,
                    "size_bytes": job.size_bytes,
                    "status": job.status,
                    "created_at": job.created_at.isoformat(),
                    "expires_at": job.expires_at.isoformat(),
                }
                for job in jobs
            ],
        }

    async def delete_account(self, context: AuthContext, password: str) -> None:
        if not context.user.password_hash:
            raise AccountDataError(
                "RECENT_REAUTHENTICATION_REQUIRED",
                "Reauthentication is required before account deletion",
                status_code=403,
            )
        try:
            valid = PASSWORD_HASHER.verify(password, context.user.password_hash)
        except Exception:
            valid = False
        if not valid:
            raise AccountDataError(
                "RECENT_REAUTHENTICATION_REQUIRED",
                "Reauthentication is required before account deletion",
                status_code=403,
            )

        owner = f"user:{context.user.id}"
        jobs = list(
            await self.db.scalars(select(DocumentJob).where(DocumentJob.owner_subject == owner))
        )
        try:
            storage = PrivateDocumentStorage(self.storage_root) if jobs else None
            for job in jobs:
                if storage is None:
                    raise OSError("document storage unavailable")
                storage.delete(job.storage_key)
                if job.output_storage_key:
                    storage.delete(job.output_storage_key)
        except (OSError, ValueError) as exc:
            raise AccountDataError(
                "ACCOUNT_CLEANUP_FAILED",
                "Account cleanup could not be completed",
                status_code=503,
            ) from exc

        await self.db.execute(
            update(AuthSession)
            .where(and_(AuthSession.user_id == context.user.id, AuthSession.revoked_at.is_(None)))
            .values(revoked_at=_now())
        )
        await self.db.execute(delete(DocumentJob).where(DocumentJob.owner_subject == owner))
        await self.db.execute(delete(Favorite).where(Favorite.user_id == context.user.id))
        await self.db.execute(delete(Translation).where(Translation.user_id == context.user.id))
        await self.db.execute(
            delete(UserPreference).where(UserPreference.user_id == context.user.id)
        )
        await self.db.execute(
            delete(AuthActionToken).where(AuthActionToken.user_id == context.user.id)
        )
        await self.db.execute(delete(AuthSession).where(AuthSession.user_id == context.user.id))
        await self.db.execute(delete(User).where(User.id == context.user.id))
        await self.db.commit()
