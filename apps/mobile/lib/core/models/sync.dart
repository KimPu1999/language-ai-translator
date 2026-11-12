class SyncStatus {
  const SyncStatus({required this.enabled, required this.serverTime, required this.locale, required this.theme});

  factory SyncStatus.fromJson(Map<String, dynamic> json) {
    final preferences = Map<String, dynamic>.from((json['preferences'] as Map?) ?? const {});
    return SyncStatus(enabled: json['enabled'] as bool? ?? false, serverTime: DateTime.parse(json['server_time'] as String), locale: preferences['locale'] as String? ?? 'en', theme: preferences['theme'] as String? ?? 'system');
  }

  final bool enabled;
  final DateTime serverTime;
  final String locale;
  final String theme;
}

class SyncRecord {
  const SyncRecord({required this.entityType, required this.clientRecordId, required this.clientUpdatedAt, this.deleted = false, this.sourceLanguage, this.targetLanguage, this.sourceText, this.translatedText, this.provider, this.translationClientRecordId});

  final String entityType;
  final String clientRecordId;
  final DateTime clientUpdatedAt;
  final bool deleted;
  final String? sourceLanguage;
  final String? targetLanguage;
  final String? sourceText;
  final String? translatedText;
  final String? provider;
  final String? translationClientRecordId;

  factory SyncRecord.fromJson(Map<String, dynamic> json) => SyncRecord(
        entityType: json['entity_type'] as String,
        clientRecordId: json['client_record_id'] as String,
        clientUpdatedAt: DateTime.parse(json['client_updated_at'] as String),
        deleted: json['deleted'] as bool? ?? false,
        sourceLanguage: json['source_language'] as String?,
        targetLanguage: json['target_language'] as String?,
        sourceText: json['source_text'] as String?,
        translatedText: json['translated_text'] as String?,
        provider: json['provider'] as String?,
        translationClientRecordId: json['translation_client_record_id'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'entity_type': entityType,
        'client_record_id': clientRecordId,
        'client_updated_at': clientUpdatedAt.toUtc().toIso8601String(),
        'deleted': deleted,
        if (sourceLanguage != null) 'source_language': sourceLanguage,
        if (targetLanguage != null) 'target_language': targetLanguage,
        if (sourceText != null) 'source_text': sourceText,
        if (translatedText != null) 'translated_text': translatedText,
        if (provider != null) 'provider': provider,
        if (translationClientRecordId != null) 'translation_client_record_id': translationClientRecordId,
      };
}

class SyncChange extends SyncRecord {
  const SyncChange({required super.entityType, required super.clientRecordId, required super.clientUpdatedAt, required this.serverRecordId, required this.version, required this.updatedAt, super.deleted, super.sourceLanguage, super.targetLanguage, super.sourceText, super.translatedText, super.provider, super.translationClientRecordId});

  factory SyncChange.fromJson(Map<String, dynamic> json) => SyncChange(
        entityType: json['entity_type'] as String,
        clientRecordId: json['client_record_id'] as String,
        clientUpdatedAt: DateTime.parse(json['client_updated_at'] as String),
        serverRecordId: json['server_record_id']?.toString(),
        version: json['version'] as int? ?? 1,
        updatedAt: DateTime.parse(json['updated_at'] as String),
        deleted: json['deleted'] as bool? ?? false,
        sourceLanguage: json['source_language'] as String?,
        targetLanguage: json['target_language'] as String?,
        sourceText: json['source_text'] as String?,
        translatedText: json['translated_text'] as String?,
        provider: json['provider'] as String?,
        translationClientRecordId: json['translation_client_record_id'] as String?,
      );

  final String? serverRecordId;
  final int version;
  final DateTime updatedAt;
}

class SyncChanges {
  const SyncChanges({required this.items, required this.nextCursor, required this.hasMore});

  factory SyncChanges.fromJson(Map<String, dynamic> json) => SyncChanges(items: (json['items'] as List<dynamic>? ?? const []).map((item) => SyncChange.fromJson(Map<String, dynamic>.from(item as Map))).toList(), nextCursor: json['next_cursor'] as String?, hasMore: json['has_more'] as bool? ?? false);

  final List<SyncChange> items;
  final String? nextCursor;
  final bool hasMore;
}
