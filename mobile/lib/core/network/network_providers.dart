import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/local/secure_token_store.dart';
import '../../data/local/token_store.dart';
import '../../data/remote/auth_api.dart';
import '../../data/remote/users_api.dart';
import '../../features/auth/providers/auth_controller.dart';
import 'api_client.dart';
import 'auth_interceptor.dart';

final Provider<TokenStore> tokenStoreProvider = Provider<TokenStore>((ref) {
  return SecureTokenStore();
});

final Provider<Dio> dioProvider = Provider<Dio>((ref) {
  final Dio dio = buildApiDio();
  dio.interceptors.add(
    AuthInterceptor(
      dio: dio,
      authApi: AuthApi(dio),
      tokenStore: ref.watch(tokenStoreProvider),
      onSessionExpired: () async {
        await ref.read(authControllerProvider.notifier).logout();
      },
    ),
  );
  return dio;
});

final Provider<AuthApi> authApiProvider = Provider<AuthApi>((ref) {
  return AuthApi(ref.watch(dioProvider));
});

final Provider<UsersApi> usersApiProvider = Provider<UsersApi>((ref) {
  return UsersApi(ref.watch(dioProvider));
});
