import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/geo/haversine.dart';
import 'course_creation_state.dart';
import 'hole_draft.dart';

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

  void updateLayout({required String layoutName, required int holeCount}) {
    state = state.copyWith(layoutName: layoutName, holeCount: holeCount);
  }

  void completeLayoutStep() {
    if (!state.canLeaveLayoutStep) {
      return;
    }
    final List<HoleDraft> holes = List.generate(state.holeCount, (index) {
      final int number = index + 1;
      return state.holes.firstWhere(
        (hole) => hole.number == number,
        orElse: () => HoleDraft(number: number),
      );
    });
    state = state.copyWith(currentStep: 2, holes: holes);
  }

  void updateHolePar(int number, int par) {
    _updateHole(number, (hole) => hole.copyWith(par: par));
  }

  void updateHoleDistance(int number, double? distanceM) {
    _updateHole(
      number,
      (hole) => hole.copyWith(distanceM: distanceM, distanceIsManual: true),
    );
  }

  void captureTee(
    int number, {
    required double latitude,
    required double longitude,
    double? accuracyM,
  }) {
    _updateHole(
      number,
      (hole) => _autoFillDistance(
        hole.copyWith(
          teeLatitude: latitude,
          teeLongitude: longitude,
          teeAccuracyM: accuracyM,
        ),
      ),
    );
  }

  void captureBasket(
    int number, {
    required double latitude,
    required double longitude,
    double? accuracyM,
  }) {
    _updateHole(
      number,
      (hole) => _autoFillDistance(
        hole.copyWith(
          basketLatitude: latitude,
          basketLongitude: longitude,
          basketAccuracyM: accuracyM,
        ),
      ),
    );
  }

  /// Recomputes distance from the tee/basket coordinates once both are
  /// captured, unless the user has already typed their own value.
  HoleDraft _autoFillDistance(HoleDraft hole) {
    if (hole.distanceIsManual || !hole.hasTee || !hole.hasBasket) {
      return hole;
    }
    final double distanceM =
        haversineKm(
          hole.teeLatitude!,
          hole.teeLongitude!,
          hole.basketLatitude!,
          hole.basketLongitude!,
        ) *
        1000;
    return hole.copyWith(distanceM: distanceM);
  }

  void _updateHole(int number, HoleDraft Function(HoleDraft hole) update) {
    state = state.copyWith(
      holes: [
        for (final HoleDraft hole in state.holes)
          if (hole.number == number) update(hole) else hole,
      ],
    );
  }

  void completeHolesStep() {
    state = state.copyWith(currentStep: 3);
  }

  void goBack() {
    if (state.currentStep > 0) {
      state = state.copyWith(currentStep: state.currentStep - 1);
    }
  }
}
