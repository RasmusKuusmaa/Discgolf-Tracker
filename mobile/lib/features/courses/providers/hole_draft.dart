import 'package:freezed_annotation/freezed_annotation.dart';

part 'hole_draft.freezed.dart';

/// In-progress edits for one hole within the course creation wizard.
/// Accuracy readouts are capture-time feedback only — they aren't part of
/// the synced [Hole] model and never leave this screen.
@freezed
abstract class HoleDraft with _$HoleDraft {
  const factory HoleDraft({
    required int number,
    @Default(3) int par,
    double? distanceM,
    @Default(false) bool distanceIsManual,
    double? teeLatitude,
    double? teeLongitude,
    double? teeAccuracyM,
    double? basketLatitude,
    double? basketLongitude,
    double? basketAccuracyM,
  }) = _HoleDraft;
}

extension HoleDraftX on HoleDraft {
  bool get hasTee => teeLatitude != null && teeLongitude != null;

  bool get hasBasket => basketLatitude != null && basketLongitude != null;
}
