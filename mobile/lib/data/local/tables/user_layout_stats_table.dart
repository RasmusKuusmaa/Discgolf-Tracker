import 'package:drift/drift.dart';

import 'syncable_columns.dart';

class UserLayoutStats extends Table with SyncableColumns {
  TextColumn get userId => text()();
  TextColumn get layoutId => text()();
  IntColumn get roundsPlayed => integer().withDefault(const Constant(0))();
  IntColumn get totalScoreToPar => integer().withDefault(const Constant(0))();
  IntColumn get bestScoreToPar => integer().nullable()();
  DateTimeColumn get lastPlayedAt => dateTime()();
}
