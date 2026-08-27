import 'package:drift/drift.dart';

import 'syncable_columns.dart';

class RoundPlayers extends Table with SyncableColumns {
  TextColumn get roundId => text()();
  TextColumn get userId => text().nullable()();
  TextColumn get guestName => text().nullable()();
  IntColumn get position => integer()();
  BoolColumn get isScorekeeper => boolean().withDefault(const Constant(false))();
}
