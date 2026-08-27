import 'package:freezed_annotation/freezed_annotation.dart';

part 'hole.freezed.dart';

@freezed
abstract class Hole with _$Hole {
  const factory Hole({
    required String id,
    required String layoutId,
    required int number,
    required int par,
    double? distanceM,
    double? teeLatitude,
    double? teeLongitude,
    double? basketLatitude,
    double? basketLongitude,
    double? elevationDeltaM,
    String? notes,
  }) = _Hole;
}
