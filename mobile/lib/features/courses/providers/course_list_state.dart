import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../domain/models/course.dart';

part 'course_list_state.freezed.dart';

enum CourseSort { name, distance }

@freezed
abstract class CourseListState with _$CourseListState {
  const factory CourseListState({
    @Default(<Course>[]) List<Course> courses,
    @Default('') String query,
    @Default(CourseSort.name) CourseSort sort,
    @Default(false) bool isLoading,
    double? userLatitude,
    double? userLongitude,
  }) = _CourseListState;
}
