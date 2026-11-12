import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';
import 'package:path/path.dart' as path;

import '../models/ocr.dart';
import '../models/document.dart';
import '../models/speech.dart';
import '../models/translation.dart';

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
  ApiClient({Dio? dio})
      : _dio = dio ?? Dio(BaseOptions(baseUrl: apiBaseUrl, connectTimeout: const Duration(seconds: 8), sendTimeout: const Duration(seconds: 8), receiveTimeout: const Duration(seconds: 12)));

  final Dio _dio;

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

