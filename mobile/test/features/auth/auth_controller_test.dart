import 'package:dio/dio.dart';
import 'package:discgolf_tracker/core/network/network_providers.dart';
import 'package:discgolf_tracker/data/remote/auth_api.dart';
import 'package:discgolf_tracker/data/remote/users_api.dart';
import 'package:discgolf_tracker/domain/models/auth_state.dart';
import 'package:discgolf_tracker/domain/models/auth_tokens.dart';
import 'package:discgolf_tracker/features/auth/providers/auth_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';
import '../../support/fake_jwt.dart';
import '../../support/in_memory_token_store.dart';

const Map<String, dynamic> _userJson = {
  'id': 'user-1',
  'email': 'ace@example.com',
  'username': 'ace',
  'display_name': 'Ace Thrower',
  'avatar_url': null,
  'home_city': null,
  'country': null,
  'profile_visibility': 'public',
  'stats_visibility': 'public',
  'allow_friend_requests': true,
};

/// Flushes pending microtasks so fire-and-forget async work (like
/// [AuthController]'s session restore, kicked off from `build()`) settles
/// before assertions run.
Future<void> _settle() async {
  for (var i = 0; i < 20; i++) {
    await Future<void>.delayed(Duration.zero);
  }
}

ProviderContainer _containerWith(
  FakeHttpClientAdapter adapter, {
  AuthTokens? storedTokens,
}) {
  final Dio dio = Dio()..httpClientAdapter = adapter;
  final container = ProviderContainer(
    overrides: [
      tokenStoreProvider.overrideWithValue(InMemoryTokenStore(storedTokens)),
      authApiProvider.overrideWithValue(AuthApi(dio)),
      usersApiProvider.overrideWithValue(UsersApi(dio)),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  group('AuthController', () {
    test('restores an authenticated session from stored tokens', () async {
      final AuthTokens stored = AuthTokens(
        accessToken: 'stored-access',
        refreshToken: 'stored-refresh',
        accessExpiresAt: DateTime.now().toUtc().add(const Duration(minutes: 15)),
      );
      final adapter = FakeHttpClientAdapter({
        'GET /users/me': (options) {
          expect(options.headers['Authorization'], 'Bearer stored-access');
          return FakeHttpClientAdapter.json(_userJson, 200);
        },
      });
      final container = _containerWith(adapter, storedTokens: stored);

      container.read(authControllerProvider);
      await _settle();

      final AuthState state = container.read(authControllerProvider);
      expect(state, isA<AuthAuthenticated>());
      expect((state as AuthAuthenticated).user.username, 'ace');
    });

    test('resolves to unauthenticated when there is no stored session', () async {
      final adapter = FakeHttpClientAdapter({});
      final container = _containerWith(adapter);

      container.read(authControllerProvider);
      await _settle();

      expect(container.read(authControllerProvider), isA<AuthUnauthenticated>());
    });

    test('login success moves to authenticated with the returned user', () async {
      final adapter = FakeHttpClientAdapter({
        'POST /auth/login': (options) => FakeHttpClientAdapter.json({
          'access_token': fakeJwt(exp: 9999999999),
          'refresh_token': 'refresh-token',
        }, 200),
        'GET /users/me': (options) => FakeHttpClientAdapter.json(_userJson, 200),
      });
      final container = _containerWith(adapter);
      container.read(authControllerProvider);
      await _settle();

      await container
          .read(authControllerProvider.notifier)
          .login(identifier: 'ace', password: 'password1');

      final AuthState state = container.read(authControllerProvider);
      expect(state, isA<AuthAuthenticated>());
      expect((state as AuthAuthenticated).user.username, 'ace');
    });

    test('login failure moves to error with the server message', () async {
      final adapter = FakeHttpClientAdapter({
        'POST /auth/login': (options) => FakeHttpClientAdapter.json({
          'code': 'invalid_credentials',
          'message': 'Incorrect email/username or password',
        }, 401),
      });
      final container = _containerWith(adapter);
      container.read(authControllerProvider);
      await _settle();

      await container
          .read(authControllerProvider.notifier)
          .login(identifier: 'ace', password: 'wrong-password');

      final AuthState state = container.read(authControllerProvider);
      expect(state, isA<AuthError>());
      expect((state as AuthError).message, 'Incorrect email/username or password');
    });
  });
}
