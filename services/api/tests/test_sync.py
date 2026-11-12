from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.account_errors import AccountDataError
from app.main import app
from app.models.user import User
from app.models.user_preference import UserPreference
from app.schemas.sync import SyncPreviewRequest, SyncRecordInput
from app.services.auth import AuthContext
from app.services.sync import SyncService, _cursor, _decode_cursor, _incoming_is_stale


def context() -> AuthContext:
    return AuthContext(
        user=User(id=uuid4(), email="sync@example.com", is_active=True),
        session=None,  # type: ignore[arg-type]
        transport="bearer",
    )


class PreviewDB:
    def __init__(self, enabled: bool) -> None:
        self.preference = UserPreference(user_id=uuid4(), sync_enabled=enabled)

    async def get(self, model, _user_id):
        return self.preference if model is UserPreference else None

    def add(self, _value) -> None:
        pass

    async def flush(self) -> None:
        pass


def translation_record(**overrides) -> SyncRecordInput:
    values = {
        "entity_type": "translation",
        "client_record_id": "mobile-1",
        "client_updated_at": datetime.now(UTC),
        "source_language": "en",
        "target_language": "my",
        "source_text": "Hello",
        "translated_text": "မင်္ဂလာပါ",
        "provider": "local",
    }
    values.update(overrides)
    return SyncRecordInput(**values)


@pytest.mark.asyncio
async def test_sync_routes_are_authenticated_and_never_guest_accessible():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        paths = (
            "/api/v1/sync/status",
            "/api/v1/sync/changes",
            "/api/v1/sync/preview",
            "/api/v1/sync/import",
        )
        for path in paths:
            response = (
                await client.get(path)
                if path.endswith(("status", "changes"))
                else await client.post(path, json={"records": []})
            )
            assert response.status_code == 401, (path, response.text)
            assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_sync_requires_explicit_consent_before_preview():
    service = SyncService(PreviewDB(enabled=False))
    with pytest.raises(AccountDataError) as error:
        await service.preview(context(), SyncPreviewRequest(records=[translation_record()]))
    assert error.value.code == "SYNC_CONSENT_REQUIRED"


@pytest.mark.asyncio
async def test_sync_preview_accepts_unicode_and_rejects_unsupported_language():
    service = SyncService(PreviewDB(enabled=True))
    payload = SyncPreviewRequest(
        records=[
            translation_record(),
            translation_record(client_record_id="bad", source_language="xx"),
        ]
    )
    response = await service.preview(context(), payload)
    assert response.accepted_count == 1
    assert response.rejected_count == 1
    assert response.items[1].reason == "UNSUPPORTED_LANGUAGE"


def test_sync_cursor_is_opaque_and_round_trips():
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    value = _cursor(timestamp, uuid4())
    decoded = _decode_cursor(value)
    assert decoded is not None
    assert decoded[0] == timestamp


def test_sync_tombstone_wins_against_equal_or_older_offline_writes():
    from app.models.sync_record import SyncRecord

    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    tombstone = SyncRecord(
        user_id=uuid4(),
        entity_type="translation",
        client_record_id="record-1",
        client_updated_at=timestamp,
        payload_hash="0" * 64,
        payload={},
        deleted_at=timestamp,
        updated_at=timestamp,
    )
    assert _incoming_is_stale(tombstone, timestamp, "f" * 64)
    assert _incoming_is_stale(tombstone, datetime(2025, 12, 31, tzinfo=UTC), "f" * 64)


def test_sync_migration_has_consent_ledger_and_tombstones():
    migration = Path(__file__).parents[1] / "alembic/versions/0010_private_sync.py"
    content = migration.read_text()
    assert "sync_enabled" in content
    assert "sync_records" in content
    assert "deleted_at" in content
    assert "uq_sync_records_client" in content
