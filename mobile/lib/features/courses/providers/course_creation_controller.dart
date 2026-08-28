import 'package:riverpod_annotation/riverpod_annotation.dart';

import 'course_creation_state.dart';

part 'course_creation_controller.g.dart';

/// Owns the in-progress draft for the multi-step course creation flow.
/// Scoped to the flow's routes — each time a user starts creating a course
/// this rebuilds fresh, so a previous abandoned draft never leaks in.
@riverpod
class CourseCreationController extends _$CourseCreationController {
  @override
  CourseCreationState build() => const CourseCreationState();

  void updateBasics({
    required String name,
    String? description,
    String? city,
    String? country,
  }) {
    state = state.copyWith(
      name: name,
      description: description,
      city: city,
      country: country,
    );
  }

  void setLocation(double latitude, double longitude) {
    state = state.copyWith(latitude: latitude, longitude: longitude);
  }

  void completeBasicsStep() {
    if (!state.canLeaveBasicsStep) {
      return;
    }
    state = state.copyWith(currentStep: 1);
  }
}
