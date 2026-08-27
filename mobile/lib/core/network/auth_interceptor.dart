import 'package:dio/dio.dart';

import '../../data/local/token_store.dart';
import '../../data/remote/auth_api.dart';
import '../../domain/models/auth_tokens.dart';

/// Attaches the current access token to outgoing requests and transparently
/// refreshes it once when a request fails with 401, retrying the original
/// request afterwards.
///
/// Concurrent 401s share a single in-flight refresh call instead of each
/// triggering their own. If the refresh itself fails, stored tokens are
/// cleared and [onSessionExpired] is invoked so the caller can drop the user
/// back to the login screen.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required this.dio,
    required this.authApi,
    required this.tokenStore,
    required this.onSessionExpired,
  });

  static const String _retriedFlag = 'auth_interceptor_retried';

  final Dio dio;
  final AuthApi authApi;
  final TokenStore tokenStore;
  final Future<void> Function() onSessionExpired;

  Future<AuthTokens>? _refreshInFlight;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final AuthTokens? tokens = await tokenStore.readTokens();
    if (tokens != null) {
      options.headers['Authorization'] = 'Bearer ${tokens.accessToken}';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final bool isAuthRoute = err.requestOptions.path.startsWith('/auth/');
    final bool alreadyRetried = err.requestOptions.extra[_retriedFlag] == true;

    if (err.response?.statusCode != 401 || isAuthRoute || alreadyRetried) {
      handler.next(err);
      return;
    }

    try {
      final AuthTokens refreshed = await _refresh();
      final RequestOptions retryOptions = err.requestOptions
        ..extra[_retriedFlag] = true
        ..headers['Authorization'] = 'Bearer ${refreshed.accessToken}';
      final Response<dynamic> response = await dio.fetch<dynamic>(retryOptions);
      handler.resolve(response);
    } on Object {
      await tokenStore.clearTokens();
      await onSessionExpired();
      handler.next(err);
    }
  }

  Future<AuthTokens> _refresh() {
    return _refreshInFlight ??= _performRefresh();
  }

  Future<AuthTokens> _performRefresh() async {
    try {
      final AuthTokens? current = await tokenStore.readTokens();
      if (current == null) {
        throw StateError('No refresh token available to refresh with');
      }
      final AuthTokens refreshed = await authApi.refresh(current.refreshToken);
      await tokenStore.saveTokens(refreshed);
      return refreshed;
    } finally {
      _refreshInFlight = null;
    }
  }
}
