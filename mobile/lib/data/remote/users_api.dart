import 'package:dio/dio.dart';

import '../../core/errors/api_exception.dart';

/// Thin wrapper around the `/users/*` endpoints not owned by `AuthApi`.
class UsersApi {
  UsersApi(this._dio);

  final Dio _dio;

  /// Best-effort check only: a taken username with a private profile also
  /// 404s, so `true` is not a hard guarantee — the register call remains
  /// the source of truth and still surfaces a conflict if this was wrong.
  Future<bool> isUsernameAvailable(String username) async {
    try {
      await _dio.get<Map<String, dynamic>>('/users/$username');
      return false;
    } on DioException catch (exception) {
      if (exception.response?.statusCode == 404) {
        return true;
      }
      throw ApiException.fromDioException(exception);
    }
  }
}
