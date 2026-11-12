# ruff: noqa: E501
from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.account_errors import AccountDataError
from app.models.favorite import Favorite
from app.models.sync_record import SyncRecord
from app.models.translation import Translation
from app.models.user_preference import UserPreference
from app.providers.translation.azure import SUPPORTED_LANGUAGE_CODES
from app.schemas.sync import (
    SyncChangesResponse,
    SyncConsentRequest,
    SyncImportItem,
    SyncImportRequest,
    SyncImportResponse,
    SyncPreferencesRequest,
    SyncPreviewItem,
    SyncPreviewRequest,
    SyncPreviewResponse,
    SyncRecordInput,
    SyncRecordResponse,
    SyncStatusResponse,
)
from app.services.auth import AuthContext

MAX_BATCH = 50
MAX_PAYLOAD_BYTES = 256_000


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _payload(record: SyncRecordInput) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.model_dump(mode="json").items()
        if key not in {"entity_type", "client_record_id", "client_updated_at", "deleted"} and value is not None
    }


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _cursor(updated_at: datetime, record_id: UUID) -> str:
    raw = json.dumps({"updated_at": _aware(updated_at).isoformat(), "id": str(record_id)}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(value: str | None) -> tuple[datetime, UUID] | None:
    if not value:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode())
        return _aware(datetime.fromisoformat(data["updated_at"])), UUID(data["id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AccountDataError("INVALID_SYNC_CURSOR", "The sync cursor is invalid", status_code=400) from exc


def _response(record: SyncRecord) -> SyncRecordResponse:
    data = {} if record.deleted_at is not None else dict(record.payload or {})
    return SyncRecordResponse(
        entity_type=record.entity_type,
        client_record_id=record.client_record_id,
        server_record_id=record.server_record_id,
        version=record.version,
        client_updated_at=record.client_updated_at,
        updated_at=record.updated_at,
        deleted=record.deleted_at is not None,
        **{key: data.get(key) for key in ("source_language", "target_language", "source_text", "translated_text", "provider", "translation_client_record_id")},
    )


def _incoming_is_stale(existing: SyncRecord, incoming_time: datetime, incoming_hash: str) -> bool:
    existing_time = _aware(existing.client_updated_at)
    if existing.deleted_at is not None and incoming_time <= existing_time:
        return True
    return incoming_time < existing_time or (
        incoming_time == existing_time and incoming_hash <= existing.payload_hash
    )


class SyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _preference(self, user_id: UUID) -> UserPreference:
        preference = await self.db.get(UserPreference, user_id)
        if preference is None:
            preference = UserPreference(user_id=user_id, sync_enabled=False)
            self.db.add(preference)
            await self.db.flush()
        return preference

    async def _require_enabled(self, context: AuthContext) -> UserPreference:
        preference = await self._preference(context.user.id)
        if not preference.sync_enabled:
            raise AccountDataError("SYNC_CONSENT_REQUIRED", "Enable private cloud sync before syncing data", status_code=403)
        return preference

    async def status(self, context: AuthContext) -> SyncStatusResponse:
        preference = await self._preference(context.user.id)
        return SyncStatusResponse(
            enabled=preference.sync_enabled,
            server_time=_now(),
            preferences={"locale": preference.locale, "theme": preference.theme},
        )

    async def set_consent(self, context: AuthContext, payload: SyncConsentRequest) -> SyncStatusResponse:
        preference = await self._preference(context.user.id)
        preference.sync_enabled = payload.enabled
        await self.db.commit()
        return await self.status(context)

    async def update_preferences(self, context: AuthContext, payload: SyncPreferencesRequest) -> SyncStatusResponse:
        preference = await self._require_enabled(context)
        if payload.locale is not None:
            preference.locale = payload.locale
        if payload.theme is not None:
            preference.theme = payload.theme
        await self.db.commit()
        return await self.status(context)

    @staticmethod
    def _validate_size(records: list[SyncRecordInput]) -> None:
        if len(records) > MAX_BATCH:
            raise AccountDataError("SYNC_BATCH_TOO_LARGE", "Sync batches are limited to 50 records", status_code=413)
        size = len(json.dumps([record.model_dump(mode="json") for record in records], ensure_ascii=False).encode())
        if size > MAX_PAYLOAD_BYTES:
            raise AccountDataError("SYNC_PAYLOAD_TOO_LARGE", "The sync payload is too large", status_code=413)

    @staticmethod
    def _record_validation(record: SyncRecordInput) -> str | None:
        if record.entity_type == "translation" and not record.deleted:
            if record.source_language not in SUPPORTED_LANGUAGE_CODES or record.target_language not in SUPPORTED_LANGUAGE_CODES:
                return "UNSUPPORTED_LANGUAGE"
            if record.source_language == record.target_language:
                return "INVALID_LANGUAGE_PAIR"
        return None

    async def preview(self, context: AuthContext, payload: SyncPreviewRequest) -> SyncPreviewResponse:
        await self._require_enabled(context)
        self._validate_size(payload.records)
        items: list[SyncPreviewItem] = []
        for record in payload.records:
            reason = self._record_validation(record)
            items.append(SyncPreviewItem(client_record_id=record.client_record_id, entity_type=record.entity_type, accepted=reason is None, reason=reason))
        return SyncPreviewResponse(
            accepted_count=sum(item.accepted for item in items),
            rejected_count=sum(not item.accepted for item in items),
            items=items,
        )

    async def _existing(self, context: AuthContext, record: SyncRecordInput) -> SyncRecord | None:
        return await self.db.scalar(select(SyncRecord).where(
            SyncRecord.user_id == context.user.id,
            SyncRecord.entity_type == record.entity_type,
            SyncRecord.client_record_id == record.client_record_id,
        ))

    async def _materialize_translation(self, context: AuthContext, record: SyncRecordInput, sync: SyncRecord | None) -> UUID:
        translation = await self.db.get(Translation, sync.server_record_id) if sync and sync.server_record_id else None
        if translation is not None and translation.user_id != context.user.id:
            raise AccountDataError("SYNC_OWNERSHIP_ERROR", "The sync record is not owned by this account", status_code=403)
        if translation is None:
            translation = Translation(
                user_id=context.user.id,
                source_language_code=record.source_language or "",
                target_language_code=record.target_language or "",
                source_text=record.source_text or "",
                translated_text=record.translated_text or "",
                provider=record.provider or "unknown",
                created_at=_now(),
            )
            self.db.add(translation)
            await self.db.flush()
        else:
            translation.source_language_code = record.source_language or translation.source_language_code
            translation.target_language_code = record.target_language or translation.target_language_code
            translation.source_text = record.source_text or translation.source_text
            translation.translated_text = record.translated_text or translation.translated_text
            translation.provider = record.provider or translation.provider
        return translation.id

    async def _materialize_favorite(self, context: AuthContext, record: SyncRecordInput, sync: SyncRecord | None) -> UUID | None:
        translation_sync = await self.db.scalar(select(SyncRecord).where(
            SyncRecord.user_id == context.user.id,
            SyncRecord.entity_type == "translation",
            SyncRecord.client_record_id == record.translation_client_record_id,
        ))
        if translation_sync is None or translation_sync.deleted_at is not None or translation_sync.server_record_id is None:
            raise AccountDataError("SYNC_TRANSLATION_NOT_FOUND", "The favorite translation is not available", status_code=422)
        favorite = await self.db.scalar(select(Favorite).where(
            Favorite.user_id == context.user.id, Favorite.translation_id == translation_sync.server_record_id
        ))
        if favorite is None:
            favorite = Favorite(user_id=context.user.id, translation_id=translation_sync.server_record_id, created_at=_now())
            self.db.add(favorite)
            await self.db.flush()
        return favorite.id

    async def import_records(self, context: AuthContext, payload: SyncImportRequest) -> SyncImportResponse:
        await self._require_enabled(context)
        self._validate_size(payload.records)
        results: list[SyncImportItem] = []
        for record in payload.records:
            reason = self._record_validation(record)
            if reason:
                results.append(SyncImportItem(client_record_id=record.client_record_id, entity_type=record.entity_type, status="rejected", error_code=reason))
                continue
            existing = await self._existing(context, record)
            incoming_time = _aware(record.client_updated_at)
            incoming_payload = _payload(record)
            incoming_hash = _hash(incoming_payload)
            if existing is not None:
                if _incoming_is_stale(existing, incoming_time, incoming_hash):
                    results.append(SyncImportItem(client_record_id=record.client_record_id, entity_type=record.entity_type, status="ignored", server_record_id=existing.server_record_id, version=existing.version))
                    continue
            server_id: UUID | None = None
            try:
                if record.deleted:
                    if existing and existing.server_record_id:
                        if record.entity_type == "translation":
                            await self.db.execute(delete(Favorite).where(Favorite.translation_id == existing.server_record_id, Favorite.user_id == context.user.id))
                            await self.db.execute(delete(Translation).where(Translation.id == existing.server_record_id, Translation.user_id == context.user.id))
                        else:
                            await self.db.execute(delete(Favorite).where(Favorite.id == existing.server_record_id, Favorite.user_id == context.user.id))
                    server_id = existing.server_record_id if existing else None
                    result_status = "deleted"
                elif record.entity_type == "translation":
                    server_id = await self._materialize_translation(context, record, existing)
                    result_status = "applied"
                else:
                    server_id = await self._materialize_favorite(context, record, existing)
                    result_status = "applied"
            except AccountDataError as exc:
                results.append(SyncImportItem(client_record_id=record.client_record_id, entity_type=record.entity_type, status="rejected", error_code=exc.code))
                continue
            if existing is None:
                existing = SyncRecord(user_id=context.user.id, entity_type=record.entity_type, client_record_id=record.client_record_id, version=1, created_at=_now())
                self.db.add(existing)
            else:
                existing.version += 1
            now = _now()
            existing.server_record_id = server_id
            existing.client_updated_at = incoming_time
            existing.payload_hash = incoming_hash
            existing.payload = incoming_payload
            existing.deleted_at = now if record.deleted else None
            existing.updated_at = now
            await self.db.flush()
            results.append(SyncImportItem(client_record_id=record.client_record_id, entity_type=record.entity_type, status=result_status, server_record_id=server_id, version=existing.version))
        await self.db.commit()
        return SyncImportResponse(items=results)

    async def changes(self, context: AuthContext, cursor: str | None, limit: int) -> SyncChangesResponse:
        await self._require_enabled(context)
        decoded = _decode_cursor(cursor)
        filters = [SyncRecord.user_id == context.user.id]
        if decoded:
            updated_at, record_id = decoded
            filters.append(or_(SyncRecord.updated_at > updated_at, and_(SyncRecord.updated_at == updated_at, SyncRecord.id > record_id)))
        rows = list(await self.db.scalars(select(SyncRecord).where(and_(*filters)).order_by(SyncRecord.updated_at.asc(), SyncRecord.id.asc()).limit(limit + 1)))
        has_more = len(rows) > limit
        rows = rows[:limit]
        return SyncChangesResponse(items=[_response(row) for row in rows], next_cursor=_cursor(rows[-1].updated_at, rows[-1].id) if rows else cursor, has_more=has_more)


__all__ = ["SyncService"]
