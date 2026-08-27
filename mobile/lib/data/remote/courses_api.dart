import 'package:dio/dio.dart';

import '../../core/errors/api_exception.dart';
import '../../domain/models/course.dart';
import '../../domain/models/hole.dart';
import '../../domain/models/layout.dart';

/// Thin wrapper around the `/courses` endpoints.
///
/// Responses nest `location` as `{lat, lng}` and omit the parent id on
/// nested layouts/holes, so parsing is done by hand here rather than via
/// generated `fromJson` — the flattened, foreign-key-carrying shape these
/// return is what [CourseRepository] caches locally.
class CoursesApi {
  CoursesApi(this._dio);

  final Dio _dio;

  Future<List<Course>> fetchList({String? query, String? country}) async {
    final Map<String, dynamic> json = await _get('/courses', <String, dynamic>{
      'q': ?query,
      'country': ?country,
    });
    return (json['items'] as List<dynamic>)
        .map((e) => _courseFromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<Course>> fetchNearby({
    required double lat,
    required double lng,
    required double radiusKm,
  }) async {
    final Map<String, dynamic> json = await _get('/courses/nearby', <String, dynamic>{
      'lat': lat,
      'lng': lng,
      'radius_km': radiusKm,
    });
    return (json['items'] as List<dynamic>)
        .map((e) => _courseFromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Course> fetchById(String id) async {
    final Map<String, dynamic> json = await _get('/courses/$id', const <String, dynamic>{});
    return _courseFromJson(json);
  }

  Future<Map<String, dynamic>> _get(String path, Map<String, dynamic> queryParameters) async {
    try {
      final Response<Map<String, dynamic>> response = await _dio.get<Map<String, dynamic>>(
        path,
        queryParameters: queryParameters,
      );
      return response.data!;
    } on DioException catch (exception) {
      throw ApiException.fromDioException(exception);
    }
  }
}

Course _courseFromJson(Map<String, dynamic> json) {
  final Map<String, dynamic> location = json['location'] as Map<String, dynamic>;
  final String courseId = json['id'] as String;
  return Course(
    id: courseId,
    name: json['name'] as String,
    slug: json['slug'] as String,
    description: json['description'] as String?,
    city: json['city'] as String?,
    region: json['region'] as String?,
    country: json['country'] as String?,
    latitude: (location['lat'] as num).toDouble(),
    longitude: (location['lng'] as num).toDouble(),
    createdById: json['created_by_id'] as String?,
    visibility: json['visibility'] as String,
    status: json['status'] as String,
    isVerified: json['is_verified'] as bool? ?? false,
    layouts: (json['layouts'] as List<dynamic>? ?? const <dynamic>[])
        .map((e) => _layoutFromJson(e as Map<String, dynamic>, courseId))
        .toList(),
  );
}

Layout _layoutFromJson(Map<String, dynamic> json, String courseId) {
  final String layoutId = json['id'] as String;
  return Layout(
    id: layoutId,
    courseId: courseId,
    name: json['name'] as String,
    holeCount: json['hole_count'] as int,
    parTotal: json['par_total'] as int,
    totalDistanceM: (json['total_distance_m'] as num?)?.toDouble(),
    difficulty: json['difficulty'] as String?,
    isDefault: json['is_default'] as bool? ?? false,
    isActive: json['is_active'] as bool? ?? true,
    holes: (json['holes'] as List<dynamic>? ?? const <dynamic>[])
        .map((e) => _holeFromJson(e as Map<String, dynamic>, layoutId))
        .toList(),
  );
}

Hole _holeFromJson(Map<String, dynamic> json, String layoutId) {
  final Map<String, dynamic>? tee = json['tee_location'] as Map<String, dynamic>?;
  final Map<String, dynamic>? basket = json['basket_location'] as Map<String, dynamic>?;
  return Hole(
    id: json['id'] as String,
    layoutId: layoutId,
    number: json['number'] as int,
    par: json['par'] as int,
    distanceM: (json['distance_m'] as num?)?.toDouble(),
    teeLatitude: (tee?['lat'] as num?)?.toDouble(),
    teeLongitude: (tee?['lng'] as num?)?.toDouble(),
    basketLatitude: (basket?['lat'] as num?)?.toDouble(),
    basketLongitude: (basket?['lng'] as num?)?.toDouble(),
    elevationDeltaM: (json['elevation_delta_m'] as num?)?.toDouble(),
    notes: json['notes'] as String?,
  );
}
