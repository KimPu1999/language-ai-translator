import 'package:dio/dio.dart';

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

  Future<TranslationResponse> translateText({required String? sourceLanguage, required String targetLanguage, required String text}) async {
    final raw = await _request<Map<String, dynamic>>(() => _dio.post<Map<String, dynamic>>('/api/v1/translations/text', data: {
      'source_language': sourceLanguage,
      'target_language': targetLanguage,
      'text': text,
    }));
    return TranslationResponse.fromJson(raw);
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

