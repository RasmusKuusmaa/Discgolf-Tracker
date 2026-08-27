import 'package:freezed_annotation/freezed_annotation.dart';

import 'layout.dart';

part 'course.freezed.dart';

@freezed
abstract class Course with _$Course {
  const factory Course({
    required String id,
    required String name,
    required String slug,
    String? description,
    String? city,
    String? region,
    String? country,
    required double latitude,
    required double longitude,
    String? createdById,
    required String visibility,
    required String status,
    @Default(false) bool isVerified,
    @Default(<Layout>[]) List<Layout> layouts,
  }) = _Course;
}
