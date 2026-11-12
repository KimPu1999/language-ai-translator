import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.rate_limit import InMemorySpeechRateLimiter, get_speech_rate_limiter
from app.db.session import get_db
from app.main import app
from app.providers.speech.base import (
    SpeechRecognitionResult,
    SpeechSynthesisResult,
)
from app.providers.speech.registry import SpeechProviderRegistry, get_speech_registry
from app.services.audio import AudioInputError, _convert


@dataclass
class FakeRecognition:
    name: str = "fake-speech"

    async def recognize(self, *, audio_data: bytes, locale: str):
        assert audio_data.startswith(b"RIFF")
        return SpeechRecognitionResult("မင်္ဂလာပါ", locale, self.name)


@dataclass
class FakeSynthesis:
    name: str = "fake-speech"

    async def synthesize(self, *, text: str, locale: str, voice: str | None = None):
        return SpeechSynthesisResult(b"RIFF0000WAVEfmt ", locale, voice or "voice", self.name)


class FakeDb:
    def __init__(self):
        self.events = []

    def add(self, event):
        self.events.append(event)

    async def commit(self):
        pass

    async def rollback(self):
        pass


def override_dependencies(registry, limiter=None, db=None):
    app.dependency_overrides[get_speech_registry] = lambda: registry
    app.dependency_overrides[get_speech_rate_limiter] = lambda: (
        limiter or InMemorySpeechRateLimiter(Settings())
    )
    app.dependency_overrides[get_db] = lambda: db or FakeDb()


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_transcribe_returns_real_provider_transcript_and_metadata(monkeypatch):
    db = FakeDb()
    registry = SpeechProviderRegistry(FakeRecognition(), None)
    override_dependencies(registry, db=db)

    async def convert(data):
        assert data == b"recorded"
        return b"RIFF0000WAVEfmt ", 1200

    monkeypatch.setattr("app.api.v1.endpoints.voice.convert_to_pcm_wav", convert)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voice/transcribe?locale=my-MM",
            content=b"recorded",
            headers={"Content-Type": "audio/webm"},
        )

    assert response.status_code == 200
    assert response.json()["transcript"] == "မင်္ဂလာပါ"
    assert response.json()["locale"] == "my-MM"
    assert db.events[0].operation == "transcribe"
    assert not hasattr(db.events[0], "transcript")


@pytest.mark.asyncio
async def test_transcribe_rejects_unsupported_and_oversized_audio():
    override_dependencies(SpeechProviderRegistry(FakeRecognition(), None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unsupported = await client.post(
            "/api/v1/voice/transcribe?locale=en-US",
            content=b"audio",
            headers={"Content-Type": "application/pdf"},
        )
        oversized = await client.post(
            "/api/v1/voice/transcribe?locale=en-US",
            content=b"x" * (5 * 1024 * 1024 + 1),
            headers={"Content-Type": "audio/wav"},
        )
    assert unsupported.status_code == 422
    assert unsupported.json()["error"]["code"] == "UNSUPPORTED_AUDIO_FORMAT"
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "AUDIO_TOO_LARGE"


@pytest.mark.asyncio
async def test_transcribe_maps_conversion_failure_and_cleans_converter_boundary(monkeypatch):
    db = FakeDb()
    override_dependencies(SpeechProviderRegistry(FakeRecognition(), None), db=db)

    async def fail(_):
        raise AudioInputError("AUDIO_TOO_LONG", "Audio must be 15 seconds or shorter")

    monkeypatch.setattr("app.api.v1.endpoints.voice.convert_to_pcm_wav", fail)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voice/transcribe?locale=en-US",
            content=b"recorded",
            headers={"Content-Type": "audio/wav"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AUDIO_TOO_LONG"
    assert db.events[0].error_code == "AUDIO_TOO_LONG"


def test_audio_converter_cleans_temporary_files_after_failure(monkeypatch):
    created: list[Path] = []

    class TemporaryDirectory:
        def __init__(self, prefix):
            self.prefix = prefix

        def __enter__(self):
            path = Path(mkdtemp(prefix="lingua-test-audio-"))
            created.append(path)
            return str(path)

        def __exit__(self, *_):
            for item in created:
                for child in item.iterdir():
                    child.unlink()
                item.rmdir()

    calls = 0

    def fake_run(command, *, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return subprocess.CompletedProcess(command, 0, b"1.0\n", b"")
        return subprocess.CompletedProcess(command, 1, b"", b"invalid")

    monkeypatch.setattr("app.services.audio.tempfile.TemporaryDirectory", TemporaryDirectory)
    monkeypatch.setattr("app.services.audio._run", fake_run)
    with pytest.raises(AudioInputError, match="Audio could not be converted"):
        _convert(b"not-a-real-audio-file")
    assert created and not created[0].exists()


@pytest.mark.asyncio
async def test_synthesize_returns_wav_and_rejects_unconfigured_provider():
    db = FakeDb()
    override_dependencies(SpeechProviderRegistry(None, FakeSynthesis()), db=db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voice/synthesize",
            json={"text": "မင်္ဂလာပါ", "locale": "my-MM", "voice": "my-MM-NilarNeural"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content.startswith(b"RIFF")
    assert db.events[0].character_count == 9

    override_dependencies(SpeechProviderRegistry(None, None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unavailable = await client.post(
            "/api/v1/voice/synthesize",
            json={"text": "hello", "locale": "en-US", "voice": "en-US-JennyNeural"},
        )
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "SPEECH_ENGINE_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_speech_rate_limit_is_enforced():
    limiter = InMemorySpeechRateLimiter(Settings(speech_rate_limit_requests=1))
    override_dependencies(SpeechProviderRegistry(None, FakeSynthesis()), limiter=limiter)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"text": "hello", "locale": "en-US", "voice": "en-US-JennyNeural"}
        first = await client.post("/api/v1/voice/synthesize", json=payload)
        second = await client.post("/api/v1/voice/synthesize", json=payload)
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "SPEECH_RATE_LIMIT_EXCEEDED"
