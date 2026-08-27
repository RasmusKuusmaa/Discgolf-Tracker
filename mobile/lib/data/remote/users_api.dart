import 'package:dio/dio.dart';

import '../../core/errors/api_exception.dart';
import '../../domain/models/user.dart';

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

  Future<User> updateMe({
    String? displayName,
    String? avatarUrl,
    String? homeCity,
    String? profileVisibility,
    String? statsVisibility,
    bool? allowFriendRequests,
  }) async {
    final Map<String, dynamic> body = <String, dynamic>{
      'display_name': ?displayName,
      'avatar_url': ?avatarUrl,
      'home_city': ?homeCity,
      'profile_visibility': ?profileVisibility,
      'stats_visibility': ?statsVisibility,
      'allow_friend_requests': ?allowFriendRequests,
    };
    try {
      final Response<Map<String, dynamic>> response = await _dio.patch<Map<String, dynamic>>(
        '/users/me',
        data: body,
      );
      return User.fromJson(response.data!);
    } on DioException catch (exception) {
      throw ApiException.fromDioException(exception);
    }
  }
}
