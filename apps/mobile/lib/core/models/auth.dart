class AuthUser {
  const AuthUser({required this.id, required this.email, required this.emailVerified, required this.isActive, required this.createdAt});

  factory AuthUser.fromJson(Map<String, dynamic> json) => AuthUser(
        id: json['id'].toString(),
        email: json['email'] as String,
        emailVerified: json['email_verified'] as bool? ?? false,
        isActive: json['is_active'] as bool? ?? true,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  final String id;
  final String email;
  final bool emailVerified;
  final bool isActive;
  final DateTime createdAt;
}

class AuthResponse {
  const AuthResponse({required this.user, this.accessToken, this.tokenType, this.csrfToken, required this.expiresAt});

  factory AuthResponse.fromJson(Map<String, dynamic> json) => AuthResponse(
        user: AuthUser.fromJson(Map<String, dynamic>.from(json['user'] as Map)),
        accessToken: json['access_token'] as String?,
        tokenType: json['token_type'] as String?,
        csrfToken: json['csrf_token'] as String?,
        expiresAt: DateTime.parse(json['expires_at'] as String),
      );

  final AuthUser user;
  final String? accessToken;
  final String? tokenType;
  final String? csrfToken;
  final DateTime expiresAt;
}

class AuthSession {
  const AuthSession({required this.id, this.deviceName, this.userAgent, required this.createdAt, required this.lastSeenAt, required this.expiresAt, required this.current});

  factory AuthSession.fromJson(Map<String, dynamic> json) => AuthSession(
        id: json['id'].toString(),
        deviceName: json['device_name'] as String?,
        userAgent: json['user_agent'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
        lastSeenAt: DateTime.parse(json['last_seen_at'] as String),
        expiresAt: DateTime.parse(json['expires_at'] as String),
        current: json['current'] as bool? ?? false,
      );

  final String id;
  final String? deviceName;
  final String? userAgent;
  final DateTime createdAt;
  final DateTime lastSeenAt;
  final DateTime expiresAt;
  final bool current;
}

class UserProfile {
  const UserProfile({required this.id, required this.email, this.displayName, required this.emailVerified, required this.createdAt});

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        id: json['id'].toString(),
        email: json['email'] as String,
        displayName: json['display_name'] as String?,
        emailVerified: json['email_verified'] as bool? ?? false,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  final String id;
  final String email;
  final String? displayName;
  final bool emailVerified;
  final DateTime createdAt;
}

class UserPreferences {
  const UserPreferences({required this.locale, required this.theme, required this.historyEnabled, this.syncEnabled = false});

  factory UserPreferences.fromJson(Map<String, dynamic> json) => UserPreferences(
        locale: json['locale'] as String? ?? 'en',
        theme: json['theme'] as String? ?? 'system',
        historyEnabled: json['history_enabled'] as bool? ?? false,
        syncEnabled: json['sync_enabled'] as bool? ?? false,
      );

  final String locale;
  final String theme;
  final bool historyEnabled;
  final bool syncEnabled;
}

class AccountHistoryItem {
  const AccountHistoryItem({required this.id, required this.sourceLanguage, required this.targetLanguage, required this.sourceText, required this.translatedText, required this.provider, required this.createdAt});

  factory AccountHistoryItem.fromJson(Map<String, dynamic> json) => AccountHistoryItem(
        id: json['id'].toString(),
        sourceLanguage: json['source_language'] as String,
        targetLanguage: json['target_language'] as String,
        sourceText: json['source_text'] as String,
        translatedText: json['translated_text'] as String,
        provider: json['provider'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  final String id;
  final String sourceLanguage;
  final String targetLanguage;
  final String sourceText;
  final String translatedText;
  final String provider;
  final DateTime createdAt;
}

class AccountHistoryResponse {
  const AccountHistoryResponse({required this.items, required this.total, required this.limit, required this.offset});

  factory AccountHistoryResponse.fromJson(Map<String, dynamic> json) => AccountHistoryResponse(
        items: (json['items'] as List<dynamic>? ?? const []).map((item) => AccountHistoryItem.fromJson(Map<String, dynamic>.from(item as Map))).toList(),
        total: json['total'] as int? ?? 0,
        limit: json['limit'] as int? ?? 20,
        offset: json['offset'] as int? ?? 0,
      );

  final List<AccountHistoryItem> items;
  final int total;
  final int limit;
  final int offset;
}

class FavoriteItem {
  const FavoriteItem({required this.id, required this.translationId, required this.createdAt, required this.translation});

  factory FavoriteItem.fromJson(Map<String, dynamic> json) => FavoriteItem(
        id: json['id'].toString(),
        translationId: json['translation_id'].toString(),
        createdAt: DateTime.parse(json['created_at'] as String),
        translation: AccountHistoryItem.fromJson(Map<String, dynamic>.from(json['translation'] as Map)),
      );

  final String id;
  final String translationId;
  final DateTime createdAt;
  final AccountHistoryItem translation;
}

class FavoritesResponse {
  const FavoritesResponse({required this.items, required this.total, required this.limit, required this.offset});

  factory FavoritesResponse.fromJson(Map<String, dynamic> json) => FavoritesResponse(
        items: (json['items'] as List<dynamic>? ?? const []).map((item) => FavoriteItem.fromJson(Map<String, dynamic>.from(item as Map))).toList(),
        total: json['total'] as int? ?? 0,
        limit: json['limit'] as int? ?? 20,
        offset: json['offset'] as int? ?? 0,
      );

  final List<FavoriteItem> items;
  final int total;
  final int limit;
  final int offset;
}
