import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.rate_limit import InMemoryTranslationRateLimiter, get_translation_rate_limiter
from app.main import app
from app.models.translation_usage_event import TranslationUsageEvent
from app.providers.translation.base import (
    LanguageDetectionResult,
    TranslationProvider,
    TranslationResult,
)
from app.providers.translation.registry import TranslationProviderRegistry, get_translation_registry
from app.repositories.usage import record_usage_event
from app.schemas.translation import TextTranslationRequest


class FakeProvider(TranslationProvider):
    name = "fake"
    capabilities = frozenset({"text_translation", "language_detection"})

    async def translate(self, *, source_language, target_language, text):
        return TranslationResult(text, self.name, source_language)

    async def detect(self, *, text):
        return LanguageDetectionResult("my", 0.99, [])


class MetadataSession:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_rate_limit_returns_structured_429_and_request_id():
    async def fake_db():
        yield MetadataSession()

    app.dependency_overrides[get_translation_registry] = lambda: TranslationProviderRegistry(
        [FakeProvider()]
    )
    limiter = InMemoryTranslationRateLimiter(
        Settings(
            database_url="postgresql+asyncpg://localhost:5432/lingua",
            rate_limit_requests=1,
            rate_limit_characters=5000,
        )
    )
    app.dependency_overrides[get_translation_rate_limiter] = lambda: limiter
    from app.db.session import get_db

    app.dependency_overrides[get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post(
                "/api/v1/translations/text",
                json={"target_language": "en", "text": "မင်္ဂလာပါ"},
            )
            second = await client.post(
                "/api/v1/translations/text",
                json={"target_language": "en", "text": "hello"},
            )
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert second.json()["error"]["request_id"] == second.headers["x-request-id"]
        assert second.headers["retry-after"]
    finally:
        app.dependency_overrides.clear()


def test_burmese_unicode_is_counted_as_characters_not_bytes():
    value = TextTranslationRequest(target_language="en", text="မင်္ဂလာပါ")
    assert len(value.text.encode()) > len(value.text)
    assert len(value.text) < 5000


@pytest.mark.asyncio
async def test_character_usage_limit_is_separate_from_request_limit():
    limiter = InMemoryTranslationRateLimiter(
        Settings(
            database_url="postgresql+asyncpg://localhost:5432/lingua",
            rate_limit_requests=10,
            rate_limit_characters=2,
        )
    )
    assert (await limiter.check("client", "ab")).allowed
    decision = await limiter.check("client", "c")
    assert not decision.allowed
    assert decision.code == "CHARACTER_USAGE_LIMIT_EXCEEDED"


def test_nfc_normalization_is_applied_before_limit():
    value = TextTranslationRequest(target_language="my", text="e\u0301")
    assert value.text == "é"


def test_metadata_usage_event_has_no_translation_text_fields():
    session = MetadataSession()

    import asyncio

    asyncio.run(
        record_usage_event(
            session,
            request_id="request-1",
            operation="translate",
            provider="azure",
            source_language="my",
            target_language="en",
            character_count=8,
            status="success",
            latency_ms=12,
        )
    )
    event = session.added[0]
    assert isinstance(event, TranslationUsageEvent)
    assert not hasattr(event, "source_text")
    assert not hasattr(event, "translated_text")


def test_registry_does_not_advertise_unsupported_capabilities():
    provider = FakeProvider()
    provider.capabilities = frozenset({"text_translation"})
    registry = TranslationProviderRegistry([provider])
    assert registry.get_for("text_translation") is provider
    assert registry.get_for("language_detection") is None
