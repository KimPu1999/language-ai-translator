import time
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app
from app.providers.speech.azure import AzureSpeechRecognitionProvider, AzureSpeechSynthesisProvider
from app.providers.speech.base import SpeechProviderError
from app.providers.speech.mapping import SPEECH_LANGUAGE_CAPABILITIES
from app.providers.speech.registry import SpeechProviderRegistry, get_speech_registry


class FakePushStream:
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    def close(self):
        pass


class FakeSpeechConfig:
    def __init__(self, subscription, region):
        self.subscription = subscription
        self.region = region


class FakeRecognizer:
    def __init__(self, speech_config, audio_config):
        self.audio_config = audio_config

    def recognize_once(self):
        return SimpleNamespace(reason=FakeSdk.ResultReason.RecognizedSpeech, text="မင်္ဂလာပါ")


class FakeSynthesizer:
    def __init__(self, speech_config, audio_config):
        self.speech_config = speech_config

    def speak_text_async(self, text):
        return SimpleNamespace(
            get=lambda: SimpleNamespace(
                reason=FakeSdk.ResultReason.SynthesizingAudioCompleted,
                audio_data=b"RIFF0000WAVEfmt ",
            )
        )


class FakeSdk:
    class ResultReason:
        RecognizedSpeech = "recognized"
        NoMatch = "no_match"
        SynthesizingAudioCompleted = "synthesized"

    SpeechConfig = FakeSpeechConfig
    SpeechRecognizer = FakeRecognizer
    SpeechSynthesizer = FakeSynthesizer
    audio = SimpleNamespace(
        PushAudioInputStream=FakePushStream,
        AudioConfig=lambda stream: SimpleNamespace(stream=stream),
    )


def speech_settings(**overrides):
    return Settings(
        azure_speech_key="test-key",
        azure_speech_region="southeastasia",
        **overrides,
    )


def test_speech_credentials_must_be_configured_together():
    with pytest.raises(ValidationError):
        Settings(azure_speech_key="only-a-key")
    with pytest.raises(ValidationError):
        Settings(azure_speech_region="southeastasia")


def test_speech_mapping_has_all_required_locales_and_text_codes():
    assert {item.locale for item in SPEECH_LANGUAGE_CAPABILITIES} == {
        "my-MM",
        "en-US",
        "th-TH",
        "zh-CN",
        "ja-JP",
        "ko-KR",
    }
    assert {item.text_code for item in SPEECH_LANGUAGE_CAPABILITIES} == {
        "my",
        "en",
        "th",
        "zh-Hans",
        "ja",
        "ko",
    }


@pytest.mark.asyncio
async def test_azure_speech_providers_use_sdk_and_preserve_unicode():
    settings = speech_settings()
    recognition = AzureSpeechRecognitionProvider(settings, sdk=FakeSdk)
    synthesis = AzureSpeechSynthesisProvider(settings, sdk=FakeSdk)

    recognized = await recognition.recognize(audio_data=b"wav", locale="my-MM")
    synthesized = await synthesis.synthesize(text="မင်္ဂလာပါ", locale="my-MM")

    assert recognized.text == "မင်္ဂလာပါ"
    assert recognized.locale == "my-MM"
    assert synthesized.audio_data.startswith(b"RIFF")
    assert synthesized.voice == "my-MM-NilarNeural"


@pytest.mark.asyncio
async def test_speech_provider_rejects_unknown_locale_and_empty_audio():
    provider = AzureSpeechRecognitionProvider(speech_settings(), sdk=FakeSdk)
    with pytest.raises(SpeechProviderError, match="Unsupported speech locale"):
        await provider.recognize(audio_data=b"wav", locale="en")
    with pytest.raises(SpeechProviderError, match="Audio input is required"):
        await provider.recognize(audio_data=b"", locale="en-US")


@pytest.mark.asyncio
async def test_speech_timeout_is_structured():
    provider = AzureSpeechRecognitionProvider(
        speech_settings(azure_speech_timeout_seconds=0.01), sdk=FakeSdk
    )

    def timeout(_, __):
        time.sleep(1)

    provider._recognize_sync = timeout  # type: ignore[method-assign]
    with pytest.raises(SpeechProviderError) as error:
        await provider.recognize(audio_data=b"wav", locale="en-US")
    assert error.value.code == "SPEECH_PROVIDER_TIMEOUT"
    assert error.value.status_code == 504


@pytest.mark.asyncio
async def test_speech_capabilities_do_not_expose_credentials(monkeypatch):
    registry = SpeechProviderRegistry(recognition=None, synthesis=None)
    app.dependency_overrides[get_speech_registry] = lambda: registry
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/speech/capabilities")
        assert response.status_code == 200
        body = response.json()
        assert body["provider_configured"] is False
        assert body["speech_recognition"] is False
        assert "test-key" not in response.text
    finally:
        app.dependency_overrides.clear()
