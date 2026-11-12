from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path

MAX_AUDIO_BYTES = 5 * 1024 * 1024
MAX_AUDIO_SECONDS = 15.0
MAX_PCM_WAV_BYTES = 10 * 1024 * 1024
ALLOWED_AUDIO_CONTENT_TYPES = frozenset(
    {"audio/wav", "audio/x-wav", "audio/webm", "audio/ogg", "audio/mpeg", "audio/mp4"}
)


class AudioInputError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _run(command: list[str], *, timeout: float) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=timeout,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise AudioInputError(
            "AUDIO_CONVERTER_UNAVAILABLE",
            "Audio conversion is unavailable on the API server",
            status_code=503,
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioInputError(
            "AUDIO_CONVERSION_TIMEOUT", "Audio conversion timed out", status_code=504
        ) from exc
    except OSError as exc:
        raise AudioInputError(
            "AUDIO_CONVERSION_FAILED", "Audio conversion failed", status_code=422
        ) from exc


def _convert(audio_data: bytes) -> tuple[bytes, int]:
    with tempfile.TemporaryDirectory(prefix="lingua-audio-") as directory:
        root = Path(directory)
        input_path = root / "input.audio"
        output_path = root / "output.wav"
        input_path.write_bytes(audio_data)

        probe = _run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                os.fspath(input_path),
            ],
            timeout=5,
        )
        if probe.returncode != 0:
            raise AudioInputError("INVALID_AUDIO", "Audio content could not be read")
        try:
            duration = float(probe.stdout.decode("ascii").strip())
        except (ValueError, UnicodeDecodeError):
            raise AudioInputError("INVALID_AUDIO", "Audio duration could not be read") from None
        if duration <= 0:
            raise AudioInputError("AUDIO_SILENCE_OR_EMPTY", "Audio contains no usable duration")
        if duration > MAX_AUDIO_SECONDS:
            raise AudioInputError("AUDIO_TOO_LONG", "Audio must be 15 seconds or shorter")

        converted = _run(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-v",
                "error",
                "-i",
                os.fspath(input_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                os.fspath(output_path),
            ],
            timeout=10,
        )
        if converted.returncode != 0 or not output_path.is_file():
            raise AudioInputError("INVALID_AUDIO", "Audio could not be converted")
        wav = output_path.read_bytes()
        if len(wav) > MAX_PCM_WAV_BYTES or not wav.startswith(b"RIFF") or b"WAVE" not in wav[:16]:
            raise AudioInputError("AUDIO_CONVERSION_FAILED", "Converted audio is invalid")
        return wav, round(duration * 1000)


async def convert_to_pcm_wav(audio_data: bytes) -> tuple[bytes, int]:
    return await asyncio.to_thread(_convert, audio_data)
