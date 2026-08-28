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
  }) = _CourseCreationState;
}

extension CourseCreationStateX on CourseCreationState {
  bool get hasLocation => latitude != null && longitude != null;

  bool get canLeaveBasicsStep => name.trim().isNotEmpty && hasLocation;
}
