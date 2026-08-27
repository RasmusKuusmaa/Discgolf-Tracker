import 'dart:convert';

import 'package:dio/dio.dart';

import '../../core/errors/api_exception.dart';
import '../../domain/models/auth_tokens.dart';
import '../../domain/models/user.dart';

/// Thin wrapper around the `/auth/*` and `/users/me` endpoints.
class AuthApi {
  AuthApi(this._dio);

  final Dio _dio;

  Future<AuthTokens> register({
    required String email,
    required String username,
    required String displayName,
    required String password,
  }) async {
    final Map<String, dynamic> json = await _post('/auth/register', <String, dynamic>{
      'email': email,
      'username': username,
      'display_name': displayName,
      'password': password,
    });
    return _tokensFromJson(json);
  }

  Future<AuthTokens> login({
    required String identifier,
    required String password,
  }) async {
    final Map<String, dynamic> json = await _post('/auth/login', <String, dynamic>{
      'identifier': identifier,
      'password': password,
    });
    return _tokensFromJson(json);
  }

  Future<AuthTokens> refresh(String refreshToken) async {
    final Map<String, dynamic> json = await _post('/auth/refresh', <String, dynamic>{
      'refresh_token': refreshToken,
    });
    return _tokensFromJson(json);
  }

  Future<void> logout(String refreshToken) async {
    await _post('/auth/logout', <String, dynamic>{'refresh_token': refreshToken});
  }

  Future<User> me(String accessToken) async {
    try {
      final Response<Map<String, dynamic>> response = await _dio.get<Map<String, dynamic>>(
        '/users/me',
        options: Options(headers: <String, dynamic>{'Authorization': 'Bearer $accessToken'}),
      );
      return User.fromJson(response.data!);
    } on DioException catch (exception) {
      throw ApiException.fromDioException(exception);
    }
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    try {
      final Response<Map<String, dynamic>> response = await _dio.post<Map<String, dynamic>>(
        path,
        data: body,
      );
      return response.data!;
    } on DioException catch (exception) {
      throw ApiException.fromDioException(exception);
    }
  }

  AuthTokens _tokensFromJson(Map<String, dynamic> json) {
    final String accessToken = json['access_token'] as String;
    final String refreshToken = json['refresh_token'] as String;
    return AuthTokens(
      accessToken: accessToken,
      refreshToken: refreshToken,
      accessExpiresAt: _expiryFromJwt(accessToken),
    );
  }

  DateTime _expiryFromJwt(String token) {
    final List<String> parts = token.split('.');
    if (parts.length != 3) {
      throw const ApiException(
        code: 'invalid_token',
        message: 'Access token is malformed',
        statusCode: 0,
      );
    }
    final Map<String, dynamic> payload =
        jsonDecode(utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))))
            as Map<String, dynamic>;
    final int exp = payload['exp'] as int;
    return DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
  }
}
