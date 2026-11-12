from pydantic import BaseModel, ConfigDict, Field


class VoiceSynthesisRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=5000)
    locale: str = Field(min_length=2, max_length=16)
    voice: str = Field(min_length=1, max_length=128)


class VoiceTranscriptionResponse(BaseModel):
    transcript: str
    locale: str
    provider: str
    request_id: str
