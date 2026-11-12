from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app
from app.services.document_jobs import owner_from_capability_token
from app.services.document_storage import PrivateDocumentStorage


def test_guest_capability_is_development_only_and_owner_is_hashed():
    settings = Settings(
        document_jobs_enabled=True,
        document_guest_mode_enabled=True,
        document_guest_capability_token="dev-secret",
        redis_url="redis://localhost:6379/0",
    )
    owner = owner_from_capability_token("dev-secret", settings)
    assert owner.startswith("guest:")
    assert "dev-secret" not in owner
    with pytest.raises(Exception):
        owner_from_capability_token("wrong", settings)


def test_private_storage_uses_random_keys_and_rejects_traversal(tmp_path: Path):
    storage = PrivateDocumentStorage(str(tmp_path))
    key = storage.key("txt")
    storage.write(key, b"secret")
    assert storage.read(key) == b"secret"
    assert oct((tmp_path / key).stat().st_mode & 0o777) == "0o600"
    with pytest.raises(ValueError):
        storage.read("../outside.txt")
    storage.delete(key)
    assert not storage.exists(key)


@pytest.mark.asyncio
async def test_document_jobs_are_not_exposed_without_explicit_dev_configuration():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/documents/not-a-real-job")
    assert response.status_code == 404
