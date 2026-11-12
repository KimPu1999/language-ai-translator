from pydantic import BaseModel, ConfigDict


class SpeechVoiceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    locale: str
    gender: str


class SpeechLanguageCapabilityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text_code: str
    locale: str
    stt_enabled: bool
    tts_enabled: bool
    voices: list[SpeechVoiceResponse]


class SpeechCapabilitiesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str | None
    provider_configured: bool
    speech_recognition: bool
    speech_synthesis: bool
    languages: list[SpeechLanguageCapabilityResponse]
