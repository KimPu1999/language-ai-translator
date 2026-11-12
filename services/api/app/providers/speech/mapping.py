from app.providers.speech.base import SpeechLanguageCapability, SpeechVoice

SPEECH_LANGUAGE_CAPABILITIES: tuple[SpeechLanguageCapability, ...] = (
    SpeechLanguageCapability(
        text_code="my",
        locale="my-MM",
        stt_enabled=True,
        tts_enabled=True,
        voices=(SpeechVoice("my-MM-NilarNeural", "my-MM", "Female"),),
    ),
    SpeechLanguageCapability(
        text_code="en",
        locale="en-US",
        stt_enabled=True,
        tts_enabled=True,
        voices=(
            SpeechVoice("en-US-JennyNeural", "en-US", "Female"),
            SpeechVoice("en-US-GuyNeural", "en-US", "Male"),
        ),
    ),
    SpeechLanguageCapability(
        text_code="th",
        locale="th-TH",
        stt_enabled=True,
        tts_enabled=True,
        voices=(
            SpeechVoice("th-TH-PremwadeeNeural", "th-TH", "Female"),
            SpeechVoice("th-TH-NiwatNeural", "th-TH", "Male"),
        ),
    ),
    SpeechLanguageCapability(
        text_code="zh-Hans",
        locale="zh-CN",
        stt_enabled=True,
        tts_enabled=True,
        voices=(
            SpeechVoice("zh-CN-XiaoxiaoNeural", "zh-CN", "Female"),
            SpeechVoice("zh-CN-YunxiNeural", "zh-CN", "Male"),
        ),
    ),
    SpeechLanguageCapability(
        text_code="ja",
        locale="ja-JP",
        stt_enabled=True,
        tts_enabled=True,
        voices=(
            SpeechVoice("ja-JP-NanamiNeural", "ja-JP", "Female"),
            SpeechVoice("ja-JP-KeitaNeural", "ja-JP", "Male"),
        ),
    ),
    SpeechLanguageCapability(
        text_code="ko",
        locale="ko-KR",
        stt_enabled=True,
        tts_enabled=True,
        voices=(
            SpeechVoice("ko-KR-SunHiNeural", "ko-KR", "Female"),
            SpeechVoice("ko-KR-InJoonNeural", "ko-KR", "Male"),
        ),
    ),
)

BY_LOCALE = {item.locale: item for item in SPEECH_LANGUAGE_CAPABILITIES}
