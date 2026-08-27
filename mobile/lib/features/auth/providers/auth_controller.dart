import 'dart:async';

import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/network/network_providers.dart';
import '../../../data/local/token_store.dart';
import '../../../data/remote/auth_api.dart';
import '../../../data/remote/users_api.dart';
import '../../../domain/models/auth_state.dart';
import '../../../domain/models/auth_tokens.dart';
import '../../../domain/models/user.dart';

part 'auth_controller.g.dart';

/// Owns the app's session state and restores it from stored tokens on
/// launch, so callers only ever need to watch [AuthState].
@riverpod
class AuthController extends _$AuthController {
  @override
  AuthState build() {
    unawaited(_restoreSession());
    return const AuthState.initial();
  }

  AuthApi get _authApi => ref.read(authApiProvider);
  UsersApi get _usersApi => ref.read(usersApiProvider);
  TokenStore get _tokenStore => ref.read(tokenStoreProvider);

  Future<void> _restoreSession() async {
    state = const AuthState.authenticating();
    final AuthTokens? tokens = await _tokenStore.readTokens();
    if (tokens == null) {
      state = const AuthState.unauthenticated();
      return;
    }
    try {
      final User user = await _authApi.me(tokens.accessToken);
      state = AuthState.authenticated(user);
    } on ApiException {
      await _refreshAndFetch(tokens.refreshToken);
    }
  }

  Future<void> _refreshAndFetch(String refreshToken) async {
    try {
      final AuthTokens refreshed = await _authApi.refresh(refreshToken);
      await _tokenStore.saveTokens(refreshed);
      final User user = await _authApi.me(refreshed.accessToken);
      state = AuthState.authenticated(user);
    } on ApiException {
      await _tokenStore.clearTokens();
      state = const AuthState.unauthenticated();
    }
  }

  Future<void> login({required String identifier, required String password}) async {
    state = const AuthState.authenticating();
    try {
      final AuthTokens tokens = await _authApi.login(
        identifier: identifier,
        password: password,
      );
      await _tokenStore.saveTokens(tokens);
      final User user = await _authApi.me(tokens.accessToken);
      state = AuthState.authenticated(user);
    } on ApiException catch (exception) {
      state = AuthState.error(exception.message);
    }
  }

  Future<void> register({
    required String email,
    required String username,
    required String displayName,
    required String password,
  }) async {
    state = const AuthState.authenticating();
    try {
      final AuthTokens tokens = await _authApi.register(
        email: email,
        username: username,
        displayName: displayName,
        password: password,
      );
      await _tokenStore.saveTokens(tokens);
      final User user = await _authApi.me(tokens.accessToken);
      state = AuthState.authenticated(user);
    } on ApiException catch (exception) {
      state = AuthState.error(exception.message);
    }
  }

  /// Rethrows [ApiException] on failure instead of moving to [AuthError],
  /// since an [AuthError] state is treated as logged out by the router —
  /// a failed edit should never boot an authenticated user back to login.
  Future<void> updateProfile({
    String? displayName,
    String? avatarUrl,
    String? homeCity,
    String? profileVisibility,
    String? statsVisibility,
    bool? allowFriendRequests,
  }) async {
    final User updated = await _usersApi.updateMe(
      displayName: displayName,
      avatarUrl: avatarUrl,
      homeCity: homeCity,
      profileVisibility: profileVisibility,
      statsVisibility: statsVisibility,
      allowFriendRequests: allowFriendRequests,
    );
    state = AuthState.authenticated(updated);
  }

  Future<void> logout() async {
    final AuthTokens? tokens = await _tokenStore.readTokens();
    if (tokens != null) {
      try {
        await _authApi.logout(tokens.refreshToken);
      } on ApiException {
        // Best effort — the local session is cleared regardless.
      }
    }
    await _tokenStore.clearTokens();
    state = const AuthState.unauthenticated();
  }
}
