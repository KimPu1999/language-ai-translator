class Language {
  const Language({required this.code, required this.name, required this.isSourceEnabled, required this.isTargetEnabled});

  factory Language.fromJson(Map<String, dynamic> json) => Language(
        code: json['code'] as String,
        name: json['name'] as String,
        isSourceEnabled: json['is_source_enabled'] as bool? ?? true,
        isTargetEnabled: json['is_target_enabled'] as bool? ?? true,
      );

  final String code;
  final String name;
  final bool isSourceEnabled;
  final bool isTargetEnabled;
}

class Capabilities {
  const Capabilities({required this.textTranslation, required this.providerConfigured, required this.supportedOperations});

  factory Capabilities.fromJson(Map<String, dynamic> json) => Capabilities(
        textTranslation: json['text_translation'] as bool? ?? false,
        providerConfigured: json['provider_configured'] as bool? ?? false,
        supportedOperations: (json['supported_operations'] as List<dynamic>? ?? const []).cast<String>(),
      );

  final bool textTranslation;
  final bool providerConfigured;
  final List<String> supportedOperations;
}

