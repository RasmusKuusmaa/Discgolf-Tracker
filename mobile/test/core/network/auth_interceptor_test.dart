import 'package:dio/dio.dart';
import 'package:discgolf_tracker/core/network/auth_interceptor.dart';
import 'package:discgolf_tracker/data/remote/auth_api.dart';
import 'package:discgolf_tracker/domain/models/auth_tokens.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';
import '../../support/fake_jwt.dart';
import '../../support/in_memory_token_store.dart';

AuthTokens _tokens(String label) => AuthTokens(
  accessToken: '$label-access',
  refreshToken: '$label-refresh',
  accessExpiresAt: DateTime.now().toUtc().add(const Duration(minutes: 15)),
);

void main() {
  group('AuthInterceptor', () {
    test('attaches the stored access token to outgoing requests', () async {
      final InMemoryTokenStore tokenStore = InMemoryTokenStore(_tokens('old'));
      final FakeHttpClientAdapter adapter = FakeHttpClientAdapter({
        'GET /protected': (options) => FakeHttpClientAdapter.json({'ok': true}, 200),
      });
      final Dio dio = Dio()..httpClientAdapter = adapter;
      dio.interceptors.add(
        AuthInterceptor(
          dio: dio,
          authApi: AuthApi(dio),
          tokenStore: tokenStore,
          onSessionExpired: () async {},
        ),
      );

      await dio.get<void>('/protected');

      expect(adapter.requests.single.headers['Authorization'], 'Bearer old-access');
    });

    test('refreshes once on 401 and retries the original request', () async {
      final InMemoryTokenStore tokenStore = InMemoryTokenStore(_tokens('old'));
      int protectedCalls = 0;
      final FakeHttpClientAdapter adapter = FakeHttpClientAdapter({
        'GET /protected': (options) {
          protectedCalls++;
          if (protectedCalls == 1) {
            return FakeHttpClientAdapter.json({
              'code': 'invalid_token',
              'message': 'expired',
            }, 401);
          }
          return FakeHttpClientAdapter.json({'ok': true}, 200);
        },
        'POST /auth/refresh': (options) => FakeHttpClientAdapter.json({
          'access_token': fakeJwt(exp: 9999999999),
          'refresh_token': 'new-refresh',
        }, 200),
      });
      final Dio dio = Dio()..httpClientAdapter = adapter;
      dio.interceptors.add(
        AuthInterceptor(
          dio: dio,
          authApi: AuthApi(dio),
          tokenStore: tokenStore,
          onSessionExpired: () async {},
        ),
      );

      final Response<dynamic> response = await dio.get<dynamic>('/protected');

      expect(response.statusCode, 200);
      expect(adapter.countOf('GET', '/protected'), 2);
      expect(adapter.countOf('POST', '/auth/refresh'), 1);
      expect((await tokenStore.readTokens())?.refreshToken, 'new-refresh');
    });

    test('shares a single in-flight refresh across concurrent 401s', () async {
      final InMemoryTokenStore tokenStore = InMemoryTokenStore(_tokens('old'));
      final Map<String, int> callCounts = {'/a': 0, '/b': 0};
      final FakeHttpClientAdapter adapter = FakeHttpClientAdapter({
        'GET /a': (options) {
          callCounts['/a'] = callCounts['/a']! + 1;
          return callCounts['/a'] == 1
              ? FakeHttpClientAdapter.json({}, 401)
              : FakeHttpClientAdapter.json({'ok': true}, 200);
        },
        'GET /b': (options) {
          callCounts['/b'] = callCounts['/b']! + 1;
          return callCounts['/b'] == 1
              ? FakeHttpClientAdapter.json({}, 401)
              : FakeHttpClientAdapter.json({'ok': true}, 200);
        },
        'POST /auth/refresh': (options) => FakeHttpClientAdapter.json({
          'access_token': fakeJwt(exp: 9999999999),
          'refresh_token': 'new-refresh',
        }, 200),
      });
      final Dio dio = Dio()..httpClientAdapter = adapter;
      dio.interceptors.add(
        AuthInterceptor(
          dio: dio,
          authApi: AuthApi(dio),
          tokenStore: tokenStore,
          onSessionExpired: () async {},
        ),
      );

      await Future.wait([dio.get<dynamic>('/a'), dio.get<dynamic>('/b')]);

      expect(adapter.countOf('POST', '/auth/refresh'), 1);
    });

    test('clears tokens and notifies session expiry when refresh fails', () async {
      final InMemoryTokenStore tokenStore = InMemoryTokenStore(_tokens('old'));
      bool sessionExpired = false;
      final FakeHttpClientAdapter adapter = FakeHttpClientAdapter({
        'GET /protected': (options) => FakeHttpClientAdapter.json({}, 401),
        'POST /auth/refresh': (options) => FakeHttpClientAdapter.json({
          'code': 'invalid_token',
          'message': 'expired',
        }, 401),
      });
      final Dio dio = Dio()..httpClientAdapter = adapter;
      dio.interceptors.add(
        AuthInterceptor(
          dio: dio,
          authApi: AuthApi(dio),
          tokenStore: tokenStore,
          onSessionExpired: () async {
            sessionExpired = true;
          },
        ),
      );

      await expectLater(dio.get<dynamic>('/protected'), throwsA(isA<DioException>()));

      expect(sessionExpired, isTrue);
      expect(await tokenStore.readTokens(), isNull);
    });
  });
}
