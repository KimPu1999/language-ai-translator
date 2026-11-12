from fastapi import APIRouter, Depends

from app.providers.speech.registry import SpeechProviderRegistry, get_speech_registry
from app.schemas.speech import (
    SpeechCapabilitiesResponse,
    SpeechLanguageCapabilityResponse,
    SpeechVoiceResponse,
)

router = APIRouter(prefix="/api/v1/speech", tags=["speech"])


@router.get("/capabilities", response_model=SpeechCapabilitiesResponse)
async def speech_capabilities(
    registry: SpeechProviderRegistry = Depends(get_speech_registry),
) -> SpeechCapabilitiesResponse:
    return SpeechCapabilitiesResponse(
        provider="azure" if registry.configured else None,
        provider_configured=registry.configured,
        speech_recognition=registry.recognition_configured,
        speech_synthesis=registry.synthesis_configured,
        languages=[
            SpeechLanguageCapabilityResponse(
                text_code=item.text_code,
                locale=item.locale,
                stt_enabled=item.stt_enabled and registry.recognition_configured,
                tts_enabled=item.tts_enabled and registry.synthesis_configured,
                voices=[SpeechVoiceResponse(**voice.__dict__) for voice in item.voices],
            )
            for item in registry.capabilities
        ],
    )
