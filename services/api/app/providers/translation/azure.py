from __future__ import annotations

from uuid import uuid4

import httpx

from app.core.config import Settings
from app.providers.translation.base import (
    LanguageDetectionResult,
    TranslationProvider,
    TranslationProviderError,
    TranslationResult,
)

SUPPORTED_LANGUAGE_CODES = {"en", "my", "th", "zh-Hans", "ja", "ko"}
AZURE_LANGUAGE_CODES = {code: code for code in SUPPORTED_LANGUAGE_CODES}


class AzureTranslationProvider(TranslationProvider):
    name = "azure"
    capabilities = frozenset({"text_translation", "language_detection"})

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None):
        if not settings.azure_translator_key:
            raise ValueError("Azure Translator credentials are not configured")
        self._settings = settings
        self._client = client
        self._timeout = httpx.Timeout(settings.azure_translator_timeout_seconds)

    async def translate(
        self, *, source_language: str | None, target_language: str, text: str
    ) -> TranslationResult:
        params: dict[str, str] = {"api-version": "3.0", "to": self._map_language(target_language)}
        if source_language:
            params["from"] = self._map_language(source_language)
        payload = await self._post("/translate", params=params, json=[{"Text": text}])
        try:
            item = payload[0]
            translation = item["translations"][0]
            translated_text = translation["text"]
            detected = item.get("detectedLanguage", {}).get("language")
        except (IndexError, KeyError, TypeError) as exc:
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_INVALID_RESPONSE",
                "Translation provider returned an invalid response",
            ) from exc
        if not isinstance(translated_text, str) or not translated_text:
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_INVALID_RESPONSE",
                "Translation provider returned an empty response",
            )
        return TranslationResult(
            translated_text=translated_text,
            provider=self.name,
            detected_language=detected if isinstance(detected, str) else None,
        )

    async def detect(self, *, text: str) -> LanguageDetectionResult:
        payload = await self._post("/detect", params={"api-version": "3.0"}, json=[{"Text": text}])
        try:
            item = payload[0]
            language = item["language"]
            score = item["score"]
            alternatives = item.get("alternatives", [])
        except (IndexError, KeyError, TypeError) as exc:
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_INVALID_RESPONSE",
                "Language detection provider returned an invalid response",
            ) from exc
        if not isinstance(language, str) or not isinstance(score, (int, float)):
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_INVALID_RESPONSE",
                "Language detection provider returned an invalid result",
            )
        return LanguageDetectionResult(
            language=self._canonical_language(language),
            score=float(score),
            alternatives=alternatives if isinstance(alternatives, list) else [],
        )

    async def _post(self, path: str, *, params: dict[str, str], json: list[dict[str, str]]) -> list:
        headers = {
            "Ocp-Apim-Subscription-Key": self._settings.azure_translator_key or "",
            "Content-Type": "application/json",
            "X-ClientTraceId": str(uuid4()),
        }
        if self._settings.azure_translator_region:
            headers["Ocp-Apim-Subscription-Region"] = self._settings.azure_translator_region
        try:
            if self._client is not None:
                response = await self._client.post(
                    f"{self._settings.azure_translator_endpoint}{path}",
                    params=params,
                    headers=headers,
                    json=json,
                    timeout=self._timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self._settings.azure_translator_endpoint}{path}",
                        params=params,
                        headers=headers,
                        json=json,
                    )
        except httpx.TimeoutException as exc:
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_TIMEOUT",
                "Translation provider timed out; please try again",
                status_code=504,
            ) from exc
        except httpx.RequestError as exc:
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_UNAVAILABLE",
                "Translation provider is unavailable; please try again",
            ) from exc
        if response.status_code in (401, 403):
            code = (
                "TRANSLATION_PROVIDER_UNAUTHORIZED"
                if response.status_code == 401
                else "TRANSLATION_PROVIDER_FORBIDDEN"
            )
            raise TranslationProviderError(
                code,
                "Azure Translator rejected the configured credentials",
                status_code=502,
            )
        if response.status_code == 429:
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_RATE_LIMITED",
                "Translation provider rate limit reached; please try again later",
                status_code=429,
                retry_after=response.headers.get("Retry-After"),
            )
        if response.is_error:
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_UPSTREAM_ERROR",
                "Translation provider returned an upstream error",
                status_code=502 if response.status_code < 500 else 503,
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_INVALID_RESPONSE",
                "Translation provider returned invalid JSON",
            ) from exc
        if not isinstance(data, list):
            raise TranslationProviderError(
                "TRANSLATION_PROVIDER_INVALID_RESPONSE",
                "Translation provider returned an invalid response",
            )
        return data

    @staticmethod
    def _map_language(language: str) -> str:
        try:
            return AZURE_LANGUAGE_CODES[language]
        except KeyError as exc:
            raise TranslationProviderError(
                "UNSUPPORTED_LANGUAGE",
                f"Unsupported language: {language}",
                status_code=422,
            ) from exc

    @staticmethod
    def _canonical_language(language: str) -> str:
        for canonical, azure_code in AZURE_LANGUAGE_CODES.items():
            if language.lower() == azure_code.lower():
                return canonical
        return language
