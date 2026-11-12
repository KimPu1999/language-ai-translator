import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models/auth.dart';
import '../../core/network/api_client.dart';
import '../../core/security/secure_session_store.dart';

enum AuthStatus { loading, unauthenticated, authenticated }

class AuthState {
  const AuthState({required this.status, this.user, this.error});

  const AuthState.loading() : this(status: AuthStatus.loading);
  const AuthState.unauthenticated({String? error}) : this(status: AuthStatus.unauthenticated, error: error);
  const AuthState.authenticated(AuthUser user) : this(status: AuthStatus.authenticated, user: user);

  final AuthStatus status;
  final AuthUser? user;
  final String? error;

  bool get isAuthenticated => status == AuthStatus.authenticated && user != null;
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._api, this._store, {this.onPrivateDataClear}) : super(const AuthState.loading()) {
    restore();
  }

  final ApiClient _api;
  final SessionStore _store;
  final Future<void> Function()? onPrivateDataClear;
  bool _busy = false;

  Future<void> restore() async {
    String? token;
    try {
      token = await _store.readToken();
    } catch (_) {
      state = const AuthState.unauthenticated();
      return;
    }
    if (token == null || token.isEmpty) {
      state = const AuthState.unauthenticated();
      return;
    }
    try {
      final user = await _api.getCurrentUser();
      state = AuthState.authenticated(user);
    } on ApiFailure {
      await _store.clear();
      await onPrivateDataClear?.call();
      state = const AuthState.unauthenticated();
    }
  }

  Future<bool> login({required String email, required String password}) async {
    if (_busy) return false;
    final previousUser = state.user;
    _busy = true;
    state = const AuthState.loading();
    try {
      final response = await _api.login(email: email, password: password);
      final token = response.accessToken;
      if (token == null || token.isEmpty) throw const ApiFailure('AUTH_TOKEN_MISSING', 'The server did not return a mobile session token.');
      if (previousUser != null && previousUser.id != response.user.id) await onPrivateDataClear?.call();
      await _store.saveSession(token: token, userId: response.user.id);
      state = AuthState.authenticated(response.user);
      return true;
    } on ApiFailure catch (error) {
      state = AuthState.unauthenticated(error: error.message);
      return false;
    } finally {
      _busy = false;
    }
  }

  Future<void> logout() async {
    if (_busy) return;
    _busy = true;
    try {
      if (state.isAuthenticated) await _api.logout();
    } on ApiFailure {
      // Local revocation still happens when the network is unavailable.
    } finally {
      await _store.clear();
      await onPrivateDataClear?.call();
      state = const AuthState.unauthenticated();
      _busy = false;
    }
  }

  Future<void> expire() async {
    await _store.clear();
    await onPrivateDataClear?.call();
    if (!mounted) return;
    state = const AuthState.unauthenticated(error: 'Your session expired. Please sign in again.');
  }

  Future<void> validateSession() async {
    if (!state.isAuthenticated || _busy) return;
    try {
      final user = await _api.getCurrentUser();
      if (mounted) state = AuthState.authenticated(user);
    } on ApiFailure catch (error) {
      if (error.statusCode == 401 || error.statusCode == 403) await expire();
    }
  }

  void clearError() {
    if (state.error != null) state = state.isAuthenticated ? AuthState.authenticated(state.user!) : const AuthState.unauthenticated();
  }
}
