class SpeechVoice {
  const SpeechVoice({required this.name, required this.locale, required this.gender});

  factory SpeechVoice.fromJson(Map<String, dynamic> json) => SpeechVoice(
        name: json['name'] as String,
        locale: json['locale'] as String,
        gender: json['gender'] as String,
      );

  final String name;
  final String locale;
  final String gender;
}

class SpeechLanguageCapability {
  const SpeechLanguageCapability({required this.textCode, required this.locale, required this.sttEnabled, required this.ttsEnabled, required this.voices});

  factory SpeechLanguageCapability.fromJson(Map<String, dynamic> json) => SpeechLanguageCapability(
        textCode: json['text_code'] as String,
        locale: json['locale'] as String,
        sttEnabled: json['stt_enabled'] as bool? ?? false,
        ttsEnabled: json['tts_enabled'] as bool? ?? false,
        voices: (json['voices'] as List<dynamic>? ?? const []).map((item) => SpeechVoice.fromJson(Map<String, dynamic>.from(item as Map))).toList(),
      );

  final String textCode;
  final String locale;
  final bool sttEnabled;
  final bool ttsEnabled;
  final List<SpeechVoice> voices;
}

class SpeechCapabilities {
  const SpeechCapabilities({required this.provider, required this.providerConfigured, required this.speechRecognition, required this.speechSynthesis, required this.languages});

  factory SpeechCapabilities.fromJson(Map<String, dynamic> json) => SpeechCapabilities(
        provider: json['provider'] as String?,
        providerConfigured: json['provider_configured'] as bool? ?? false,
        speechRecognition: json['speech_recognition'] as bool? ?? false,
        speechSynthesis: json['speech_synthesis'] as bool? ?? false,
        languages: (json['languages'] as List<dynamic>? ?? const []).map((item) => SpeechLanguageCapability.fromJson(Map<String, dynamic>.from(item as Map))).toList(),
      );

  final String? provider;
  final bool providerConfigured;
  final bool speechRecognition;
  final bool speechSynthesis;
  final List<SpeechLanguageCapability> languages;
}

class VoiceTranscription {
  const VoiceTranscription({required this.transcript, required this.locale, required this.provider, required this.requestId});

  factory VoiceTranscription.fromJson(Map<String, dynamic> json) => VoiceTranscription(
        transcript: json['transcript'] as String,
        locale: json['locale'] as String,
        provider: json['provider'] as String,
        requestId: json['request_id'] as String,
      );

  final String transcript;
  final String locale;
  final String provider;
  final String requestId;
}
