import pytest

from app.db.session import get_db
from app.main import app
from app.providers.translation.registry import TranslationProviderRegistry, get_translation_registry


class FakeResult:
    def __init__(self, values):
        self.values = values

    def __iter__(self):
        return iter(self.values)


class FakeSession:
    async def scalars(self, _query):
        return FakeResult([])


@pytest.mark.asyncio
async def test_live(client):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_unknown_routes_use_structured_json_errors(client):
    response = await client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_404"


@pytest.mark.asyncio
async def test_languages_api_uses_database_dependency(client):
    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    response = await client.get("/api/v1/languages")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_readiness_uses_database_check(client, db_check):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    db_check.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_provider_is_stable_and_not_persisted(client):
    response = await client.post(
        "/api/v1/translations/text",
        json={"source_language": "en", "target_language": "my", "text": "hello"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TRANSLATION_ENGINE_NOT_CONFIGURED"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


@pytest.mark.asyncio
async def test_detect_requires_configured_provider(client):
    response = await client.post("/api/v1/translations/detect", json={"text": "မင်္ဂလာပါ"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "TRANSLATION_ENGINE_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_capabilities_report_unconfigured_provider(client):
    response = await client.get("/api/v1/capabilities")
    assert response.status_code == 200
    assert response.json()["provider_configured"] is False
    assert response.json()["supported_operations"] == []


@pytest.mark.asyncio
async def test_unsupported_language_is_rejected_before_provider_call(client):
    app.dependency_overrides[get_translation_registry] = lambda: TranslationProviderRegistry([])
    response = await client.post(
        "/api/v1/translations/text",
        json={"source_language": "fr", "target_language": "my", "text": "hello"},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_LANGUAGE"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "x" * 5001])
async def test_text_length_validation(client, text):
    response = await client.post(
        "/api/v1/translations/text",
        json={"source_language": "en", "target_language": "my", "text": text},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
