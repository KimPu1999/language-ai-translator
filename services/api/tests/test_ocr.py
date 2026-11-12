from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from app.core.config import Settings
from app.core.rate_limit import RateLimitDecision, get_ocr_rate_limiter
from app.db.session import get_db
from app.main import app
from app.providers.ocr.base import OCRBlock, OCRResult
from app.providers.ocr.mapping import APPLICATION_TO_TESSERACT
from app.providers.ocr.registry import OCRProviderRegistry, get_ocr_registry
from app.providers.ocr.tesseract import TesseractOCRProvider
from app.services.ocr_image import ImageInputError, preprocess_image


def image_bytes(format_name: str = "PNG") -> bytes:
    image = Image.new("RGB", (20, 10), "white")
    output = BytesIO()
    image.save(output, format=format_name)
    return output.getvalue()


class FakeProvider:
    name = "fake-ocr"

    async def extract(self, *, image, language: str) -> OCRResult:
        del image
        return OCRResult(
            text="မင်္ဂလာပါ Hello",
            language=language,
            provider=self.name,
            blocks=(OCRBlock("Hello", 0.0, 0.0, 0.5, 1.0, 96.0),),
        )


async def fake_db():
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session


def use_fake_dependencies(monkeypatch, registry=None, limiter=None):
    monkeypatch.setitem(app.dependency_overrides, get_db, fake_db)
    if registry is not None:
        monkeypatch.setitem(
            app.dependency_overrides,
            get_ocr_registry,
            lambda: registry,
        )
    if limiter is not None:
        monkeypatch.setitem(
            app.dependency_overrides,
            get_ocr_rate_limiter,
            lambda: limiter,
        )


@pytest.mark.asyncio
async def test_ocr_capabilities_are_provider_backed(client, monkeypatch):
    registry = OCRProviderRegistry(FakeProvider(), ("my", "en"))
    use_fake_dependencies(monkeypatch, registry)
    response = await client.get("/api/v1/ocr/capabilities")
    assert response.status_code == 200
    assert response.json() == {
        "provider": "fake-ocr",
        "provider_configured": True,
        "languages": ["my", "en"],
        "experimental_languages": [],
        "consent_required": False,
    }


@pytest.mark.asyncio
async def test_ocr_extract_returns_unicode_and_normalized_boxes(client, monkeypatch):
    registry = OCRProviderRegistry(FakeProvider(), ("my", "en"))
    use_fake_dependencies(monkeypatch, registry)
    response = await client.post(
        "/api/v1/ocr/extract?language=my",
        files={"image": ("fixture.png", image_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "မင်္ဂလာပါ Hello"
    assert body["blocks"][0]["left"] == 0
    assert body["blocks"][0]["width"] == 0.5
    assert body["request_id"]


@pytest.mark.asyncio
async def test_ocr_rejects_unsupported_type_and_language(client, monkeypatch):
    registry = OCRProviderRegistry(FakeProvider(), ("my", "en"))
    use_fake_dependencies(monkeypatch, registry)
    invalid_type = await client.post(
        "/api/v1/ocr/extract?language=en",
        files={"image": ("fixture.gif", b"GIF89a", "image/gif")},
    )
    invalid_language = await client.post(
        "/api/v1/ocr/extract?language=fr",
        files={"image": ("fixture.png", image_bytes(), "image/png")},
    )
    assert invalid_type.status_code == 422
    assert invalid_type.json()["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"
    assert invalid_language.status_code == 422
    assert invalid_language.json()["error"]["code"] == "UNSUPPORTED_OCR_LANGUAGE"


@pytest.mark.asyncio
async def test_ocr_provider_unavailable(client, monkeypatch):
    use_fake_dependencies(monkeypatch, OCRProviderRegistry(None, ()))
    response = await client.post(
        "/api/v1/ocr/extract?language=en",
        files={"image": ("fixture.png", image_bytes(), "image/png")},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OCR_PROVIDER_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_cloud_ocr_requires_explicit_consent(client, monkeypatch):
    class CloudProvider(FakeProvider):
        name = "google-cloud-vision"

    use_fake_dependencies(
        monkeypatch,
        OCRProviderRegistry(CloudProvider(), ("my",), ("my",), True),
    )
    response = await client.post(
        "/api/v1/ocr/extract?language=my",
        files={"image": ("fixture.png", image_bytes(), "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OCR_CLOUD_CONSENT_REQUIRED"


def test_language_mapping_is_explicit():
    assert APPLICATION_TO_TESSERACT == {
        "my": "mya",
        "en": "eng",
        "th": "tha",
        "zh-Hans": "chi_sim",
        "ja": "jpn",
        "ko": "kor",
    }


def test_preprocessing_applies_limits_and_rejects_corrupt_data():
    settings = Settings()
    oriented = preprocess_image(image_bytes("JPEG"), settings, "image/jpeg")
    assert oriented.mode == "RGB"
    with pytest.raises(ImageInputError) as error:
        preprocess_image(b"not an image", settings, "image/png")
    assert error.value.code == "INVALID_IMAGE"


def test_preprocessing_removes_exif_and_enforces_pixels():
    settings = Settings(ocr_max_pixels=10)
    with pytest.raises(ImageInputError) as error:
        preprocess_image(image_bytes(), settings, "image/png")
    assert error.value.code == "IMAGE_TOO_LARGE"

    oriented = preprocess_image(image_bytes("JPEG"), Settings(), "image/jpeg")
    assert not oriented.getexif()


@pytest.mark.asyncio
async def test_ocr_enforces_streamed_upload_limit(client, monkeypatch):
    registry = OCRProviderRegistry(FakeProvider(), ("my", "en"))
    use_fake_dependencies(monkeypatch, registry)
    monkeypatch.setattr(
        "app.api.v1.endpoints.ocr.get_settings",
        lambda: Settings(ocr_max_upload_bytes=10),
    )
    response = await client.post(
        "/api/v1/ocr/extract?language=en",
        files={"image": ("fixture.png", image_bytes(), "image/png")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"


@pytest.mark.asyncio
async def test_ocr_quota_returns_structured_429(client, monkeypatch):
    class DeniedLimiter:
        async def check(self, key, *, input_bytes):
            del key, input_bytes
            return RateLimitDecision(False, "OCR_BYTE_USAGE_LIMIT_EXCEEDED", 7)

    use_fake_dependencies(
        monkeypatch,
        OCRProviderRegistry(FakeProvider(), ("my", "en")),
        DeniedLimiter(),
    )
    response = await client.post(
        "/api/v1/ocr/extract?language=en",
        files={"image": ("fixture.png", image_bytes(), "image/png")},
    )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "7"
    assert response.json()["error"]["code"] == "OCR_BYTE_USAGE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_tesseract_provider_normalizes_boxes_and_preserves_unicode():
    class Output:
        DICT = object()

    class FakePytesseract:
        @staticmethod
        def image_to_data(image, *, lang, output_type):
            assert image.size == (20, 10)
            assert lang == "mya"
            assert output_type is Output.DICT
            return {
                "text": ["မင်္ဂလာပါ"],
                "left": [2],
                "top": [1],
                "width": [10],
                "height": [4],
                "conf": ["88.5"],
            }

    FakePytesseract.Output = Output

    provider = TesseractOCRProvider(
        Settings(), installed_languages=frozenset({"mya"}), pytesseract_module=FakePytesseract()
    )
    result = await provider.extract(image=Image.open(BytesIO(image_bytes())), language="my")
    assert result.text == "မင်္ဂလာပါ"
    assert result.blocks[0].left == 0.1
    assert result.blocks[0].top == 0.1
