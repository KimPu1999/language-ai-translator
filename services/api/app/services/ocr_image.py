from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings

ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
CONTENT_TYPE_FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


class ImageInputError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def preprocess_image(data: bytes, settings: Settings, content_type: str) -> Image.Image:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ImageInputError(
            "UNSUPPORTED_IMAGE_TYPE", "Only JPEG, PNG, and WebP images are supported"
        )
    if not data:
        raise ImageInputError("INVALID_IMAGE", "Image input is required")
    try:
        image = Image.open(BytesIO(data))
        if image.format != CONTENT_TYPE_FORMATS[content_type]:
            raise ImageInputError(
                "IMAGE_SIGNATURE_MISMATCH", "Image content does not match its declared type"
            )
        width, height = image.size
        if width <= 0 or height <= 0 or width * height > settings.ocr_max_pixels:
            raise ImageInputError(
                "IMAGE_TOO_LARGE", "Decoded image exceeds the pixel limit", status_code=413
            )
        image.load()
        oriented = ImageOps.exif_transpose(image)
        return oriented.convert("RGB")
    except ImageInputError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageInputError("INVALID_IMAGE", "Image content could not be decoded") from exc
