import 'package:flutter_test/flutter_test.dart';

import 'package:lingua_mobile/core/models/auth.dart';
import 'package:lingua_mobile/core/network/api_client.dart';
import 'package:lingua_mobile/core/security/secure_session_store.dart';
import 'package:lingua_mobile/features/auth/auth_controller.dart';

class _MemorySessionStore implements SessionStore {
  String? token;
  String? userId;
  @override
  Future<String?> readToken() async => token;
  @override
  Future<void> saveSession({required String token, required String userId}) async { this.token = token; this.userId = userId; }
  @override
  Future<void> clear() async { token = null; userId = null; }
}

class _AuthApiClient extends ApiClient {
  _AuthApiClient(SessionStore store) : super(sessionStore: store);
  bool logoutCalled = false;
  final user = AuthUser(id: 'user-1', email: 'person@example.com', emailVerified: true, isActive: true, createdAt: DateTime.utc(2026));
  @override
  Future<AuthResponse> login({required String email, required String password, String? deviceName}) async => AuthResponse(user: user, accessToken: 'opaque-mobile-token', tokenType: 'Bearer', expiresAt: DateTime.utc(2026, 1, 2));
  @override
  Future<AuthUser> getCurrentUser() async => user;
  @override
  Future<void> logout() async => logoutCalled = true;
}

void main() {
  test('auth models preserve user and session response fields', () {
    final user = AuthUser.fromJson({'id': 'u1', 'email': 'a@example.com', 'email_verified': true, 'is_active': true, 'created_at': '2026-01-01T00:00:00Z'});
    final response = AuthResponse.fromJson({'user': {'id': 'u1', 'email': 'a@example.com', 'email_verified': true, 'is_active': true, 'created_at': '2026-01-01T00:00:00Z'}, 'access_token': 'token', 'token_type': 'Bearer', 'expires_at': '2026-01-02T00:00:00Z'});
    expect(user.email, 'a@example.com');
    expect(response.accessToken, 'token');
    expect(response.user.id, 'u1');
  });

  test('login stores the opaque bearer token and logout clears it', () async {
    final store = _MemorySessionStore();
    final api = _AuthApiClient(store);
    final controller = AuthController(api, store);
    await Future<void>.delayed(Duration.zero);
    expect(await controller.login(email: 'person@example.com', password: 'CorrectHorse9!'), isTrue);
    expect(store.token, 'opaque-mobile-token');
    expect(controller.state.isAuthenticated, isTrue);
    await controller.logout();
    expect(api.logoutCalled, isTrue);
    expect(store.token, isNull);
    expect(controller.state.isAuthenticated, isFalse);
  });

  test('session expiry clears the token without exposing it in state', () async {
    final store = _MemorySessionStore()..token = 'private-token';
    final controller = AuthController(_AuthApiClient(store), store);
    await Future<void>.delayed(Duration.zero);
    await controller.expire();
    expect(store.token, isNull);
    expect(controller.state.status, AuthStatus.unauthenticated);
    expect(controller.state.error, contains('expired'));
    expect(controller.state.error, isNot(contains('private-token')));
  });
}
