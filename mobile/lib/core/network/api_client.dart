import 'package:dio/dio.dart';

/// Base URL for the backend API.
///
/// Override at build/run time with `--dart-define=API_BASE_URL=...`.
/// Defaults to the Android emulator's alias for the host machine's
/// localhost; override for iOS simulator, physical devices, or other
/// environments.
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

Dio buildApiDio({String baseUrl = kApiBaseUrl}) {
  return Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      contentType: 'application/json',
    ),
  );
}
