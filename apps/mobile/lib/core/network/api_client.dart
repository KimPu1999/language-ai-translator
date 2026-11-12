import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';
import 'package:path/path.dart' as path;

import '../models/ocr.dart';
import '../models/document.dart';
import '../models/speech.dart';
import '../models/translation.dart';
import '../models/auth.dart';
import '../models/sync.dart';
import '../security/secure_session_store.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);

class ApiFailure implements Exception {
  const ApiFailure(this.code, this.message, {this.statusCode});

  final String code;
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({Dio? dio, SessionStore? sessionStore, this.onSessionExpired})
      : _dio = dio ?? Dio(BaseOptions(baseUrl: apiBaseUrl, connectTimeout: const Duration(seconds: 8), sendTimeout: const Duration(seconds: 8), receiveTimeout: const Duration(seconds: 12))),
        _sessionStore = sessionStore ?? SecureSessionStore() {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (options.extra['skipAuth'] != true) {
          String? token;
          try {
            token = await _sessionStore.readToken();
          } catch (_) {
            // Test hosts without a native keychain/keystore continue as guests.
          }
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
            options.extra['authAttached'] = true;
          }
        }
        handler.next(options);
      },
      onError: (error, handler) {
        final status = error.response?.statusCode;
        if ((status == 401 || status == 403) && error.requestOptions.extra['authAttached'] == true) onSessionExpired?.call();
        handler.next(error);
      },
    ));
  }

  final Dio _dio;
  final SessionStore _sessionStore;
  final void Function()? onSessionExpired;

  Future<AuthResponse> login({required String email, required String password, String? deviceName}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/auth/login', data: {'email': email, 'password': password, 'client': 'mobile', if (deviceName != null) 'device_name': deviceName}, options: Options(extra: {'skipAuth': true})));
    return AuthResponse.fromJson(raw);
  }

  Future<AuthUser> register({required String email, required String password}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/auth/register', data: {'email': email, 'password': password, 'client': 'mobile'}, options: Options(extra: {'skipAuth': true})));
    return AuthUser.fromJson(Map<String, dynamic>.from(raw['user'] as Map));
  }

  Future<void> verifyEmail(String token) async {
    await _request<dynamic>(() => _dio.post<dynamic>('/api/v1/auth/verify-email', data: {'token': token}, options: Options(extra: {'skipAuth': true})));
  }

  Future<void> resendVerification(String email) async {
    await _request<dynamic>(() => _dio.post<dynamic>('/api/v1/auth/resend-verification', data: {'email': email}, options: Options(extra: {'skipAuth': true})));
  }

  Future<void> forgotPassword(String email) async {
    await _request<dynamic>(() => _dio.post<dynamic>('/api/v1/auth/forgot-password', data: {'email': email}, options: Options(extra: {'skipAuth': true})));
  }

  Future<void> resetPassword({required String token, required String password}) async {
    await _request<dynamic>(() => _dio.post<dynamic>('/api/v1/auth/reset-password', data: {'token': token, 'password': password}, options: Options(extra: {'skipAuth': true})));
  }

  Future<AuthUser> getCurrentUser() async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/auth/me'));
    return AuthUser.fromJson(raw);
  }

  Future<void> logout() async {
    await _request<dynamic>(() => _dio.post<dynamic>('/api/v1/auth/logout'));
  }

  Future<List<AuthSession>> getSessions() async {
    final raw = await _request<List<dynamic>>(() => _dio.get<List<dynamic>>('/api/v1/auth/sessions'));
    return raw.map((item) => AuthSession.fromJson(Map<String, dynamic>.from(item as Map))).toList();
  }

  Future<void> revokeSession(String id) async {
    await _request<dynamic>(() => _dio.delete<dynamic>('/api/v1/auth/sessions/${Uri.encodeComponent(id)}'));
  }

  Future<UserProfile> getProfile() async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/profile'));
    return UserProfile.fromJson(raw);
  }

  Future<UserProfile> updateProfile({required String? displayName}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.patch<Map<String, dynamic>>('/api/v1/profile', data: {'display_name': displayName}));
    return UserProfile.fromJson(raw);
  }

  Future<UserPreferences> getPreferences() async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/preferences'));
    return UserPreferences.fromJson(raw);
  }

  Future<UserPreferences> updatePreferences({String? locale, String? theme, bool? historyEnabled}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.patch<Map<String, dynamic>>('/api/v1/preferences', data: {if (locale != null) 'locale': locale, if (theme != null) 'theme': theme, if (historyEnabled != null) 'history_enabled': historyEnabled}));
    return UserPreferences.fromJson(raw);
  }

  Future<SyncStatus> getSyncStatus() async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/sync/status'));
    return SyncStatus.fromJson(raw);
  }

  Future<SyncStatus> setSyncConsent(bool enabled) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.patch<Map<String, dynamic>>('/api/v1/sync/consent', data: {'enabled': enabled}));
    return SyncStatus.fromJson(raw);
  }

  Future<SyncStatus> updateSyncPreferences({String? locale, String? theme}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.patch<Map<String, dynamic>>('/api/v1/sync/preferences', data: {if (locale != null) 'locale': locale, if (theme != null) 'theme': theme}));
    return SyncStatus.fromJson(raw);
  }

  Future<Map<String, dynamic>> previewSync(List<SyncRecord> records) async {
    return _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/sync/preview', data: {'records': records.map((record) => record.toJson()).toList()}));
  }

  Future<Map<String, dynamic>> importSync(List<SyncRecord> records, {required String idempotencyKey}) async {
    return _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/sync/import', data: {'records': records.map((record) => record.toJson()).toList(), 'idempotency_key': idempotencyKey}, options: Options(headers: {'Idempotency-Key': idempotencyKey})));
  }

  Future<SyncChanges> getSyncChanges({String? cursor}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/sync/changes', queryParameters: {'limit': 50, if (cursor != null) 'cursor': cursor}));
    return SyncChanges.fromJson(raw);
  }

  Future<AccountHistoryResponse> getHistory({int limit = 20, int offset = 0}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/history', queryParameters: {'limit': limit, 'offset': offset}));
    return AccountHistoryResponse.fromJson(raw);
  }

  Future<AccountHistoryItem> saveHistory({required String sourceLanguage, required String targetLanguage, required String sourceText, required String translatedText, required String provider}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/history', data: {'source_language': sourceLanguage, 'target_language': targetLanguage, 'source_text': sourceText, 'translated_text': translatedText, 'provider': provider}));
    return AccountHistoryItem.fromJson(raw);
  }

  Future<void> deleteHistory(String id) async {
    await _request<dynamic>(() => _dio.delete<dynamic>('/api/v1/history/${Uri.encodeComponent(id)}'));
  }

  Future<void> clearHistory() async {
    await _request<dynamic>(() => _dio.delete<dynamic>('/api/v1/history'));
  }

  Future<FavoritesResponse> getFavorites({int limit = 20, int offset = 0}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/favorites', queryParameters: {'limit': limit, 'offset': offset}));
    return FavoritesResponse.fromJson(raw);
  }

  Future<FavoriteItem> createFavorite(String translationId) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/favorites', data: {'translation_id': translationId}));
    return FavoriteItem.fromJson(raw);
  }

  Future<void> deleteFavorite(String id) async {
    await _request<dynamic>(() => _dio.delete<dynamic>('/api/v1/favorites/${Uri.encodeComponent(id)}'));
  }

  Future<List<Map<String, dynamic>>> getLanguages() async {
    final response = await _request(() => _dio.get<List<dynamic>>('/api/v1/languages'));
    return response.map((item) => Map<String, dynamic>.from(item as Map)).toList();
  }

  Future<Map<String, dynamic>> getCapabilities() async {
    return _request(() => _dio.get<Map<String, dynamic>>('/api/v1/capabilities'));
  }

  Future<SpeechCapabilities> getSpeechCapabilities() async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/speech/capabilities'));
    return SpeechCapabilities.fromJson(raw);
  }

  Future<OcrCapabilities> getOcrCapabilities() async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/ocr/capabilities'));
    return OcrCapabilities.fromJson(raw);
  }

  Future<OcrResponse> extractOcr({required String imagePath, required String language, bool cloudConsent = false, CancelToken? cancelToken}) async {
    final extension = path.extension(imagePath).toLowerCase();
    final subtype = extension == '.png' ? 'png' : extension == '.webp' ? 'webp' : 'jpeg';
    final form = FormData.fromMap({
      'image': await MultipartFile.fromFile(imagePath, filename: path.basename(imagePath), contentType: MediaType('image', subtype)),
      'cloud_consent': cloudConsent.toString(),
    });
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/ocr/extract?language=${Uri.encodeQueryComponent(language)}', data: form, cancelToken: cancelToken, options: Options(contentType: 'multipart/form-data')));
    return OcrResponse.fromJson(raw);
  }

  Future<TranslationResponse> translateText({required String? sourceLanguage, required String targetLanguage, required String text}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/translations/text', data: {
      'source_language': sourceLanguage,
      'target_language': targetLanguage,
      'text': text,
    }));
    return TranslationResponse.fromJson(raw);
  }

  Future<DocumentJob> uploadDocument({required String filePath, String? sourceLanguage, ProgressCallback? onSendProgress, CancelToken? cancelToken}) async {
    final form = FormData.fromMap({
      'document': await MultipartFile.fromFile(filePath, filename: path.basename(filePath)),
      if (sourceLanguage != null) 'source_language': sourceLanguage,
    });
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/documents', data: form, cancelToken: cancelToken, onSendProgress: onSendProgress, options: Options(contentType: 'multipart/form-data')));
    return DocumentJob.fromJson(raw);
  }

  Future<DocumentJob> getDocument(String id, {CancelToken? cancelToken}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/documents/${Uri.encodeComponent(id)}', cancelToken: cancelToken));
    return DocumentJob.fromJson(raw);
  }

  Future<DocumentSegmentsResponse> getDocumentSegments(String id, {CancelToken? cancelToken}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.get<Map<String, dynamic>>('/api/v1/documents/${Uri.encodeComponent(id)}/segments', cancelToken: cancelToken));
    return DocumentSegmentsResponse.fromJson(raw);
  }

  Future<DocumentSegmentsResponse> updateDocumentSegments(String id, List<DocumentSegment> segments, {CancelToken? cancelToken}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.put<Map<String, dynamic>>('/api/v1/documents/${Uri.encodeComponent(id)}/segments', data: {'segments': segments.map((segment) => segment.toJson()).toList()}, cancelToken: cancelToken));
    return DocumentSegmentsResponse.fromJson(raw);
  }

  Future<DocumentJob> translateDocument({required String id, required String? sourceLanguage, required String targetLanguage, required String idempotencyKey, CancelToken? cancelToken}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/documents/${Uri.encodeComponent(id)}/translate', data: {'source_language': sourceLanguage, 'target_language': targetLanguage, 'reviewed': true}, cancelToken: cancelToken, options: Options(headers: {'Idempotency-Key': idempotencyKey})));
    return DocumentJob.fromJson(raw);
  }

  Future<DocumentJob> cancelDocument(String id, {CancelToken? cancelToken}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/documents/${Uri.encodeComponent(id)}/cancel', cancelToken: cancelToken));
    return DocumentJob.fromJson(raw);
  }

  Future<DocumentJob> retryDocument(String id, {CancelToken? cancelToken}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/documents/${Uri.encodeComponent(id)}/retry', cancelToken: cancelToken));
    return DocumentJob.fromJson(raw);
  }

  Future<void> deleteDocument(String id, {CancelToken? cancelToken}) async {
    await _request<dynamic>(() => _dio.delete<dynamic>('/api/v1/documents/${Uri.encodeComponent(id)}', cancelToken: cancelToken));
  }

  Future<DocumentDownload> downloadDocument(String id, {CancelToken? cancelToken}) async {
    try {
      final response = await _dio.get<List<int>>('/api/v1/documents/${Uri.encodeComponent(id)}/download', cancelToken: cancelToken, options: Options(responseType: ResponseType.bytes));
      final disposition = response.headers.value('content-disposition') ?? '';
      final filename = RegExp(r'filename="?([^";]+)').firstMatch(disposition)?.group(1) ?? 'translated-document';
      return DocumentDownload(bytes: response.data ?? const <int>[], filename: filename, contentType: response.headers.value('content-type') ?? 'application/octet-stream');
    } on DioException catch (error) {
      final body = error.response?.data;
      final map = body is Map ? Map<String, dynamic>.from(body) : <String, dynamic>{};
      final errorBody = map['error'] is Map ? Map<String, dynamic>.from(map['error'] as Map) : <String, dynamic>{};
      throw ApiFailure(errorBody['code'] as String? ?? 'DOWNLOAD_FAILED', errorBody['message'] as String? ?? _networkMessage(error), statusCode: error.response?.statusCode);
    }
  }

  Future<VoiceTranscription> transcribeVoice({required List<int> audioBytes, required String locale, required String mimeType, CancelToken? cancelToken}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/voice/transcribe?locale=${Uri.encodeQueryComponent(locale)}', data: audioBytes, cancelToken: cancelToken, options: Options(contentType: mimeType)));
    return VoiceTranscription.fromJson(raw);
  }

  Future<List<int>> synthesizeVoice({required String text, required String locale, required String voice, CancelToken? cancelToken}) async {
    try {
      final response = await _dio.post<List<int>>('/api/v1/voice/synthesize', data: {'text': text, 'locale': locale, 'voice': voice}, cancelToken: cancelToken, options: Options(responseType: ResponseType.bytes, contentType: Headers.jsonContentType));
      return response.data ?? const <int>[];
    } on DioException catch (error) {
      final data = error.response?.data;
      final body = data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
      final errorBody = body['error'] is Map ? Map<String, dynamic>.from(body['error'] as Map) : <String, dynamic>{};
      throw ApiFailure(errorBody['code'] as String? ?? 'NETWORK_ERROR', errorBody['message'] as String? ?? _networkMessage(error), statusCode: error.response?.statusCode);
    }
  }

  Future<T> _request<T>(Future<Response<T>> Function() request) async {
    try {
      final response = await request();
      return response.data as T;
    } on DioException catch (error) {
      final data = error.response?.data;
      final body = data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
      final errorBody = body['error'] is Map ? Map<String, dynamic>.from(body['error'] as Map) : <String, dynamic>{};
      final code = errorBody['code'] as String? ?? 'NETWORK_ERROR';
      final message = errorBody['message'] as String? ?? _networkMessage(error);
      throw ApiFailure(code, message, statusCode: error.response?.statusCode);
    } on TypeError {
      throw const ApiFailure('INVALID_RESPONSE', 'The server returned an invalid response.');
    }
  }

  String _networkMessage(DioException error) => switch (error.type) {
        DioExceptionType.connectionTimeout || DioExceptionType.receiveTimeout => 'The request timed out. Check your connection and try again.',
        DioExceptionType.connectionError => 'Could not reach Lingua. Check the API URL and your connection.',
        _ => 'Something went wrong while contacting Lingua. Please try again.',
      };
}

