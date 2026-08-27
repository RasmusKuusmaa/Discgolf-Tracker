import 'package:dio/dio.dart';

/// Mirrors the backend's `{code, message, details}` error envelope.
class ApiException implements Exception {
  const ApiException({
    required this.code,
    required this.message,
    required this.statusCode,
    this.details,
  });

  factory ApiException.fromDioException(DioException exception) {
    final Response<dynamic>? response = exception.response;
    final Object? data = response?.data;
    if (data is Map<String, dynamic>) {
      return ApiException(
        code: data['code'] as String? ?? 'unknown_error',
        message: data['message'] as String? ?? exception.message ?? 'Request failed',
        statusCode: response?.statusCode ?? 0,
        details: data['details'],
      );
    }
    return ApiException(
      code: 'network_error',
      message: exception.message ?? 'Network request failed',
      statusCode: response?.statusCode ?? 0,
    );
  }

  final String code;
  final String message;
  final int statusCode;
  final Object? details;

  @override
  String toString() => 'ApiException($code): $message';
}
