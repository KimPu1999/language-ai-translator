import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract interface class SessionStore {
  Future<String?> readToken();
  Future<void> saveSession({required String token, required String userId});
  Future<void> clear();
}

class SecureSessionStore implements SessionStore {
  SecureSessionStore({FlutterSecureStorage? storage}) : _storage = storage ?? const FlutterSecureStorage();

  static const tokenKey = 'lingua.auth.access_token';
  static const userIdKey = 'lingua.auth.user_id';
  final FlutterSecureStorage _storage;

  Future<String?> readToken() => _storage.read(key: tokenKey);

  Future<void> saveSession({required String token, required String userId}) async {
    await _storage.write(key: tokenKey, value: token);
    await _storage.write(key: userIdKey, value: userId);
  }

  Future<void> clear() async {
    await _storage.delete(key: tokenKey);
    await _storage.delete(key: userIdKey);
  }
}
