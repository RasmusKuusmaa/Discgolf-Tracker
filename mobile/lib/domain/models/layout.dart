import 'package:freezed_annotation/freezed_annotation.dart';

import 'hole.dart';

part 'layout.freezed.dart';

@freezed
abstract class Layout with _$Layout {
  const factory Layout({
    required String id,
    required String courseId,
    required String name,
    required int holeCount,
    required int parTotal,
    double? totalDistanceM,
    String? difficulty,
    @Default(false) bool isDefault,
    @Default(true) bool isActive,
    @Default(<Hole>[]) List<Hole> holes,
  }) = _Layout;
}
