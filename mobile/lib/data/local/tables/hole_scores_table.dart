import 'package:drift/drift.dart';

import 'syncable_columns.dart';

class HoleScores extends Table with SyncableColumns {
  TextColumn get roundId => text()();
  TextColumn get roundPlayerId => text()();
  TextColumn get holeId => text()();
  IntColumn get strokes => integer()();
  IntColumn get penaltyStrokes => integer().withDefault(const Constant(0))();
  BoolColumn get isCircleHit => boolean().nullable()();
  BoolColumn get isFairwayHit => boolean().nullable()();
  TextColumn get notes => text().nullable()();
}
