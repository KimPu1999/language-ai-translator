class TranslationResponse {
  const TranslationResponse({required this.translatedText, required this.provider, this.detectedLanguage, this.requestId});

  factory TranslationResponse.fromJson(Map<String, dynamic> json) => TranslationResponse(
        translatedText: json['translated_text'] as String? ?? '',
        provider: json['provider'] as String? ?? 'unknown',
        detectedLanguage: json['detected_language'] as String?,
        requestId: json['request_id'] as String?,
      );

  final String translatedText;
  final String provider;
  final String? detectedLanguage;
  final String? requestId;
}
