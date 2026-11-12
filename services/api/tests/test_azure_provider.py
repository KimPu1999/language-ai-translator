import httpx
import pytest

from app.core.config import Settings
from app.providers.translation.azure import AzureTranslationProvider
from app.providers.translation.base import TranslationProviderError


def settings(**overrides) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://localhost:5432/lingua",
        azure_translator_key="test-azure-key",
        **overrides,
    )


@pytest.mark.asyncio
async def test_translate_parses_azure_response_and_keeps_key_backend_only():
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = request.read().decode()
        return httpx.Response(
            200,
            json=[
                {
                    "detectedLanguage": {"language": "my", "score": 0.99},
                    "translations": [{"text": "Hello", "to": "en"}],
                }
            ],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await AzureTranslationProvider(settings(), client=client).translate(
            source_language="my", target_language="en", text="မင်္ဂလာပါ"
        )

    assert result.translated_text == "Hello"
    assert result.detected_language == "my"
    assert "api-version=3.0" in str(seen["url"])
    assert "from=my" in str(seen["url"])
    assert "to=en" in str(seen["url"])
    assert seen["headers"]["ocp-apim-subscription-key"] == "test-azure-key"
    assert "ocp-apim-subscription-region" not in seen["headers"]
    assert "test-azure-key" not in str(result)
    assert "မင်္ဂလာပါ" in str(seen["body"])


@pytest.mark.asyncio
async def test_translate_omits_from_for_automatic_detection():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "from" not in request.url.params
        return httpx.Response(200, json=[{"translations": [{"text": "hello"}]}])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await AzureTranslationProvider(settings(), client=client).translate(
            source_language=None, target_language="en", text="မင်္ဂလာပါ"
        )
    assert result.translated_text == "hello"


@pytest.mark.asyncio
async def test_detect_parses_language_score_and_alternatives():
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "language": "my",
                    "score": 0.98,
                    "isTranslationSupported": True,
                    "alternatives": [{"language": "th", "score": 0.01}],
                }
            ],
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await AzureTranslationProvider(settings(), client=client).detect(text="မင်္ဂလာပါ")
    assert result.language == "my"
    assert result.score == 0.98
    assert result.alternatives[0]["language"] == "th"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code", "expected_status"),
    [
        (401, "TRANSLATION_PROVIDER_UNAUTHORIZED", 502),
        (403, "TRANSLATION_PROVIDER_FORBIDDEN", 502),
        (429, "TRANSLATION_PROVIDER_RATE_LIMITED", 429),
        (500, "TRANSLATION_PROVIDER_UPSTREAM_ERROR", 503),
    ],
)
async def test_azure_status_errors_are_stable(status: int, code: str, expected_status: int):
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"Retry-After": "5"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(TranslationProviderError) as raised:
            await AzureTranslationProvider(settings(), client=client).translate(
                source_language="en", target_language="my", text="hello"
            )
    assert raised.value.code == code
    assert raised.value.status_code == expected_status


@pytest.mark.asyncio
async def test_timeout_is_mapped_without_leaking_upstream_details():
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("upstream timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(TranslationProviderError) as raised:
            await AzureTranslationProvider(settings(), client=client).translate(
                source_language="en", target_language="my", text="hello"
            )
    assert raised.value.code == "TRANSLATION_PROVIDER_TIMEOUT"
    assert raised.value.status_code == 504
    assert "upstream timed out" not in raised.value.message


def test_missing_azure_credentials_are_not_constructible():
    with pytest.raises(ValueError, match="credentials"):
        AzureTranslationProvider(
            Settings(database_url="postgresql+asyncpg://localhost:5432/lingua")
        )
