from types import SimpleNamespace

import pytest
from PIL import Image

from app.core.config import Settings
from app.providers.ocr.base import OCRProviderError
from app.providers.ocr.google import GoogleCloudVisionProvider
from app.providers.ocr.registry import OCRProviderFactory


def test_google_is_not_selected_or_enabled_by_default():
    registry = OCRProviderFactory.create(Settings())
    assert registry.consent_required is False
    assert registry.provider is None or registry.provider.name == "tesseract"


def test_google_requires_both_provider_selection_and_feature_flag():
    registry = OCRProviderFactory.create(
        Settings(ocr_provider="google-cloud-vision", ocr_google_cloud_enabled=False)
    )
    assert registry.provider is None


def test_google_marks_burmese_experimental():
    provider = GoogleCloudVisionProvider(
        Settings(ocr_google_cloud_enabled=True), client=SimpleNamespace()
    )
    assert "my" in provider.experimental_languages
    assert provider.supported_languages == ("my", "en", "th", "zh-Hans", "ja", "ko")


@pytest.mark.asyncio
async def test_google_missing_client_returns_safe_error():
    provider = GoogleCloudVisionProvider(Settings(ocr_google_cloud_enabled=False))
    with pytest.raises(OCRProviderError) as error:
        await provider.extract(image=object(), language="en")
    assert error.value.code == "OCR_PROVIDER_NOT_CONFIGURED"


def test_google_bounds_are_normalized_and_clamped():
    vertices = [
        SimpleNamespace(x=-2, y=2),
        SimpleNamespace(x=20, y=2),
        SimpleNamespace(x=20, y=12),
        SimpleNamespace(x=-2, y=12),
    ]
    assert GoogleCloudVisionProvider._bounds(vertices, 20, 10) == (0, 0.2, 1, 1)


@pytest.mark.asyncio
async def test_google_response_mapping_preserves_text_and_boxes():
    class FakeVision:
        class Image:
            def __init__(self, *, content):
                self.content = content

        class ImageContext:
            def __init__(self, *, language_hints):
                self.language_hints = language_hints

    symbol = SimpleNamespace(text="မ")
    word = SimpleNamespace(symbols=[symbol])
    paragraph = SimpleNamespace(
        words=[word],
        confidence=0.91,
        bounding_box=SimpleNamespace(
            vertices=[
                SimpleNamespace(x=2, y=1),
                SimpleNamespace(x=12, y=1),
                SimpleNamespace(x=12, y=5),
                SimpleNamespace(x=2, y=5),
            ]
        ),
    )
    response = SimpleNamespace(
        error=SimpleNamespace(message=""),
        full_text_annotation=SimpleNamespace(
            text="မ", pages=[SimpleNamespace(blocks=[SimpleNamespace(paragraphs=[paragraph])])]
        ),
    )

    class Client:
        def document_text_detection(self, *, image, image_context):
            assert image_context.language_hints == ["my"]
            assert image.content
            return response

    provider = GoogleCloudVisionProvider(
        Settings(ocr_google_cloud_enabled=True), client=Client(), vision_module=FakeVision
    )
    result = await provider.extract(image=Image.new("RGB", (20, 10)), language="my")
    assert result.text == "မ"
    assert result.blocks[0].left == 0.1
    assert result.blocks[0].confidence == 91
