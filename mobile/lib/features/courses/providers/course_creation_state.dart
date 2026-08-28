import 'package:freezed_annotation/freezed_annotation.dart';

part 'course_creation_state.freezed.dart';

@freezed
abstract class CourseCreationState with _$CourseCreationState {
  const factory CourseCreationState({
    @Default(0) int currentStep,
    @Default('') String name,
    String? description,
    String? city,
    String? country,
    double? latitude,
    double? longitude,
    @Default('') String layoutName,
    @Default(18) int holeCount,
  }) = _CourseCreationState;
}

const int minHoleCount = 1;
const int maxHoleCount = 27;

extension CourseCreationStateX on CourseCreationState {
  bool get hasLocation => latitude != null && longitude != null;

  bool get canLeaveBasicsStep => name.trim().isNotEmpty && hasLocation;

  bool get canLeaveLayoutStep =>
      layoutName.trim().isNotEmpty &&
      holeCount >= minHoleCount &&
      holeCount <= maxHoleCount;
}
