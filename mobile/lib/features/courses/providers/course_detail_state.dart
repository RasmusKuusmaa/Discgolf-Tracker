import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../domain/models/course.dart';

part 'course_detail_state.freezed.dart';

@freezed
abstract class CourseDetailState with _$CourseDetailState {
  const factory CourseDetailState({
    Course? course,
    @Default(true) bool isLoading,
    String? selectedLayoutId,
    int? bestScoreToPar,
  }) = _CourseDetailState;
}
