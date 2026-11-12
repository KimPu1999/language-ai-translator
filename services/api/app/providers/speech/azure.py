from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import Settings
from app.providers.speech.base import (
    SpeechLanguageCapability,
    SpeechProviderError,
    SpeechRecognitionProvider,
    SpeechRecognitionResult,
    SpeechSynthesisProvider,
    SpeechSynthesisResult,
)
from app.providers.speech.mapping import BY_LOCALE, SPEECH_LANGUAGE_CAPABILITIES


def _load_sdk() -> Any:
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError as exc:
        raise SpeechProviderError(
            "SPEECH_PROVIDER_DEPENDENCY_MISSING",
            "Azure Speech SDK is not installed on the API server",
        ) from exc
    return speechsdk


class _AzureSpeechProvider:
    name = "azure"
    capabilities = SPEECH_LANGUAGE_CAPABILITIES

    def __init__(self, settings: Settings, *, sdk: Any | None = None) -> None:
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise ValueError("Azure Speech credentials are not configured")
        self._settings = settings
        self._sdk = sdk

    def _sdk_or_load(self) -> Any:
        return self._sdk if self._sdk is not None else _load_sdk()

    @staticmethod
    def _capability(locale: str) -> SpeechLanguageCapability:
        try:
            return BY_LOCALE[locale]
        except KeyError as exc:
            raise SpeechProviderError(
                "UNSUPPORTED_SPEECH_LANGUAGE",
                f"Unsupported speech locale: {locale}",
                status_code=422,
            ) from exc

    async def _bounded(self, operation: Any) -> Any:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(operation), timeout=self._settings.azure_speech_timeout_seconds
            )
        except TimeoutError as exc:
            raise SpeechProviderError(
                "SPEECH_PROVIDER_TIMEOUT",
                "Azure Speech timed out; please try again",
                status_code=504,
            ) from exc
        except SpeechProviderError:
            raise
        except Exception as exc:
            raise SpeechProviderError(
                "SPEECH_PROVIDER_ERROR",
                "Azure Speech provider failed",
                status_code=502,
            ) from exc

    @staticmethod
    def _provider_error(result: Any, *, default_message: str) -> SpeechProviderError:
        details = getattr(getattr(result, "cancellation_details", None), "error_details", None)
        del details  # SDK details may contain sensitive service information.
        return SpeechProviderError(
            "SPEECH_PROVIDER_ERROR", default_message, status_code=502
        )


class AzureSpeechRecognitionProvider(_AzureSpeechProvider, SpeechRecognitionProvider):
    async def recognize(self, *, audio_data: bytes, locale: str) -> SpeechRecognitionResult:
        capability = self._capability(locale)
        if not capability.stt_enabled:
            raise SpeechProviderError(
                "SPEECH_RECOGNITION_UNAVAILABLE", "Speech recognition is unavailable"
            )
        if not audio_data:
            raise SpeechProviderError("INVALID_AUDIO", "Audio input is required", status_code=422)
        result = await self._bounded(lambda: self._recognize_sync(audio_data, locale))
        return result

    def _recognize_sync(self, audio_data: bytes, locale: str) -> SpeechRecognitionResult:
        sdk = self._sdk_or_load()
        config = sdk.SpeechConfig(
            subscription=self._settings.azure_speech_key,
            region=self._settings.azure_speech_region,
        )
        config.speech_recognition_language = locale
        stream = sdk.audio.PushAudioInputStream()
        stream.write(audio_data)
        stream.close()
        audio_config = sdk.audio.AudioConfig(stream=stream)
        recognizer = sdk.SpeechRecognizer(speech_config=config, audio_config=audio_config)
        result = recognizer.recognize_once()
        if result.reason == sdk.ResultReason.RecognizedSpeech and isinstance(result.text, str):
            return SpeechRecognitionResult(result.text, locale, self.name)
        if result.reason == sdk.ResultReason.NoMatch:
            raise SpeechProviderError(
                "SPEECH_NO_MATCH", "No speech could be recognized", status_code=422
            )
        raise self._provider_error(result, default_message="Azure Speech recognition failed")


class AzureSpeechSynthesisProvider(_AzureSpeechProvider, SpeechSynthesisProvider):
    async def synthesize(
        self, *, text: str, locale: str, voice: str | None = None
    ) -> SpeechSynthesisResult:
        capability = self._capability(locale)
        if not capability.tts_enabled:
            raise SpeechProviderError(
                "SPEECH_SYNTHESIS_UNAVAILABLE", "Speech synthesis is unavailable"
            )
        if not text.strip():
            raise SpeechProviderError("INVALID_TEXT", "Text input is required", status_code=422)
        selected_voice = voice or capability.voices[0].name
        if selected_voice not in {item.name for item in capability.voices}:
            raise SpeechProviderError(
                "UNSUPPORTED_SPEECH_VOICE", "Unsupported speech voice", status_code=422
            )
        return await self._bounded(lambda: self._synthesize_sync(text, locale, selected_voice))

    def _synthesize_sync(self, text: str, locale: str, voice: str) -> SpeechSynthesisResult:
        sdk = self._sdk_or_load()
        config = sdk.SpeechConfig(
            subscription=self._settings.azure_speech_key,
            region=self._settings.azure_speech_region,
        )
        config.speech_synthesis_voice_name = voice
        output_formats = getattr(sdk, "SpeechSynthesisOutputFormat", None)
        wav_format = getattr(output_formats, "Riff16Khz16BitMonoPcm", None)
        if wav_format is not None:
            config.set_speech_synthesis_output_format(wav_format)
        synthesizer = sdk.SpeechSynthesizer(speech_config=config, audio_config=None)
        result = synthesizer.speak_text_async(text).get()
        if result.reason == sdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = getattr(result, "audio_data", None)
            if (
                isinstance(audio_data, bytes)
                and audio_data.startswith(b"RIFF")
                and b"WAVE" in audio_data[:16]
            ):
                return SpeechSynthesisResult(audio_data, locale, voice, self.name)
        raise self._provider_error(result, default_message="Azure Speech synthesis failed")
