import 'dart:async';

import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../data/local/local_providers.dart';
import '../../../data/repositories/course_repository.dart';
import '../../../domain/models/auth_state.dart';
import '../../../domain/models/course.dart';
import '../../../domain/models/layout.dart';
import '../../auth/providers/auth_controller.dart';
import 'course_detail_state.dart';

part 'course_detail_controller.g.dart';

/// Loads a single course from the local cache first, then refreshes from
/// the server in the background, and tracks which of its layouts is
/// selected for the hole table and best-score lookup.
@riverpod
class CourseDetailController extends _$CourseDetailController {
  @override
  CourseDetailState build(String courseId) {
    unawaited(_load());
    return const CourseDetailState();
  }

  CourseRepository get _repository => ref.read(courseRepositoryProvider);

  Future<void> _load() async {
    final Course? cached = await _repository.byId(courseId);
    if (cached != null) {
      state = state.copyWith(course: cached, isLoading: false);
      await _selectDefaultLayout(cached);
    }
    try {
      final Course fresh = await _repository.refreshById(courseId);
      state = state.copyWith(course: fresh, isLoading: false);
      await _selectDefaultLayout(fresh);
    } catch (_) {
      // Offline or the server is unreachable — the cached course stands.
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> _selectDefaultLayout(Course course) async {
    if (course.layouts.isEmpty) {
      return;
    }
    final bool hasCurrentSelection =
        state.selectedLayoutId != null &&
        course.layouts.any((layout) => layout.id == state.selectedLayoutId);
    if (hasCurrentSelection) {
      return;
    }
    final Layout defaultLayout = course.layouts.firstWhere(
      (layout) => layout.isDefault,
      orElse: () => course.layouts.first,
    );
    await selectLayout(defaultLayout.id);
  }

  Future<void> selectLayout(String layoutId) async {
    state = state.copyWith(selectedLayoutId: layoutId, bestScoreToPar: null);
    final AuthState authState = ref.read(authControllerProvider);
    if (authState is! AuthAuthenticated) {
      return;
    }
    final int? bestScoreToPar = await _repository.bestScoreToPar(
      userId: authState.user.id,
      layoutId: layoutId,
    );
    if (state.selectedLayoutId == layoutId) {
      state = state.copyWith(bestScoreToPar: bestScoreToPar);
    }
  }
}
