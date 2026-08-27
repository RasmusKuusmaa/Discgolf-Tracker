import 'dart:async';

import 'package:geolocator/geolocator.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/geo/haversine.dart';
import '../../../data/local/local_providers.dart';
import '../../../data/repositories/course_repository.dart';
import '../../../domain/models/course.dart';
import 'course_list_state.dart';

part 'course_list_controller.g.dart';

/// Loads courses from the local cache first, then refreshes from the
/// server in the background. Distance sort is best-effort: if location
/// isn't available (permission denied, service off), it silently falls
/// back to name sort rather than blocking the list.
@riverpod
class CourseListController extends _$CourseListController {
  @override
  CourseListState build() {
    unawaited(_load());
    return const CourseListState(isLoading: true);
  }

  CourseRepository get _repository => ref.read(courseRepositoryProvider);

  Future<void> _load() async {
    final List<Course> cached = await _repository.all();
    state = state.copyWith(courses: _sorted(cached), isLoading: cached.isEmpty);
    unawaited(_tryLocatePosition());
    try {
      final List<Course> fresh = await _repository.refreshList();
      state = state.copyWith(courses: _sorted(fresh), isLoading: false);
    } catch (_) {
      // Offline or the server is unreachable — the cached list stands.
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> setQuery(String query) async {
    state = state.copyWith(query: query);
    final List<Course> results = query.trim().isEmpty
        ? await _repository.all()
        : await _repository.search(query);
    state = state.copyWith(courses: _sorted(results));
  }

  Future<void> setSort(CourseSort sort) async {
    state = state.copyWith(sort: sort, courses: _sorted(state.courses, sort: sort));
    if (sort == CourseSort.distance && state.userLatitude == null) {
      await _tryLocatePosition();
    }
  }

  Future<void> _tryLocatePosition() async {
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return;
      }
      if (!await Geolocator.isLocationServiceEnabled()) {
        return;
      }
      final Position position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.medium),
      );
      state = state.copyWith(
        userLatitude: position.latitude,
        userLongitude: position.longitude,
        courses: _sorted(state.courses, lat: position.latitude, lng: position.longitude),
      );
    } catch (_) {
      // No location available — distance sort/chip just stays disabled.
    }
  }

  List<Course> _sorted(List<Course> courses, {CourseSort? sort, double? lat, double? lng}) {
    final CourseSort effectiveSort = sort ?? state.sort;
    final double? effectiveLat = lat ?? state.userLatitude;
    final double? effectiveLng = lng ?? state.userLongitude;

    if (effectiveSort != CourseSort.distance || effectiveLat == null || effectiveLng == null) {
      return [...courses]..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    }
    return [...courses]..sort(
      (a, b) => haversineKm(
        effectiveLat,
        effectiveLng,
        a.latitude,
        a.longitude,
      ).compareTo(haversineKm(effectiveLat, effectiveLng, b.latitude, b.longitude)),
    );
  }
}
