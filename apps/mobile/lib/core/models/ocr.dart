class OcrBlock {
  const OcrBlock({required this.text, required this.left, required this.top, required this.width, required this.height, this.confidence});

  factory OcrBlock.fromJson(Map<String, dynamic> json) => OcrBlock(
        text: json['text'] as String? ?? '',
        left: (json['left'] as num?)?.toDouble() ?? 0,
        top: (json['top'] as num?)?.toDouble() ?? 0,
        width: (json['width'] as num?)?.toDouble() ?? 0,
        height: (json['height'] as num?)?.toDouble() ?? 0,
        confidence: (json['confidence'] as num?)?.toDouble(),
      );

  final String text;
  final double left;
  final double top;
  final double width;
  final double height;
  final double? confidence;
}

class OcrCapabilities {
  const OcrCapabilities({this.provider, required this.providerConfigured, required this.languages, this.experimentalLanguages = const [], this.consentRequired = false});

  factory OcrCapabilities.fromJson(Map<String, dynamic> json) => OcrCapabilities(
        provider: json['provider'] as String?,
        providerConfigured: json['provider_configured'] as bool? ?? false,
        languages: (json['languages'] as List<dynamic>? ?? const []).cast<String>(),
        experimentalLanguages: (json['experimental_languages'] as List<dynamic>? ?? const []).cast<String>(),
        consentRequired: json['consent_required'] as bool? ?? false,
      );

  final String? provider;
  final bool providerConfigured;
  final List<String> languages;
  final List<String> experimentalLanguages;
  final bool consentRequired;
}

class OcrResponse {
  const OcrResponse({required this.text, required this.language, required this.provider, required this.blocks, this.requestId});

  factory OcrResponse.fromJson(Map<String, dynamic> json) => OcrResponse(
        text: json['text'] as String? ?? '',
        language: json['language'] as String? ?? '',
        provider: json['provider'] as String? ?? 'unknown',
        blocks: (json['blocks'] as List<dynamic>? ?? const []).map((item) => OcrBlock.fromJson(Map<String, dynamic>.from(item as Map))).toList(),
        requestId: json['request_id'] as String?,
      );

  final String text;
  final String language;
  final String provider;
  final List<OcrBlock> blocks;
  final String? requestId;
}
