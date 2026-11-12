APPLICATION_TO_TESSERACT: dict[str, str] = {
    "my": "mya",
    "en": "eng",
    "th": "tha",
    "zh-Hans": "chi_sim",
    "ja": "jpn",
    "ko": "kor",
}

SUPPORTED_APPLICATION_LANGUAGES = tuple(APPLICATION_TO_TESSERACT)

APPLICATION_TO_GOOGLE_VISION: dict[str, str] = {
    "my": "my",
    "en": "en",
    "th": "th",
    "zh-Hans": "zh",
    "ja": "ja",
    "ko": "ko",
}
