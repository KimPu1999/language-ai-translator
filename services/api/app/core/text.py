import unicodedata

MAX_TEXT_CHARACTERS = 5000


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def character_count(value: str) -> int:
    """Count Unicode scalar values after NFC normalization.

    This avoids byte-counting Burmese or other multibyte input while matching
    the provider's documented character-based request limit.
    """
    return len(normalize_text(value))
