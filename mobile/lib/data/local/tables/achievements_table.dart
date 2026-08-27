import 'package:drift/drift.dart';

import 'syncable_columns.dart';

/// Denormalized: the achievement's static definition plus this user's
/// unlock progress against it, since that's always read together and the
/// definitions are effectively read-only reference data.
class Achievements extends Table with SyncableColumns {
  TextColumn get code => text()();
  TextColumn get name => text()();
  TextColumn get description => text()();
  TextColumn get icon => text()();
  TextColumn get category => text()();
  IntColumn get tier => integer().withDefault(const Constant(1))();
  IntColumn get xpReward => integer()();
  TextColumn get criteria => text()();
  DateTimeColumn get unlockedAt => dateTime().nullable()();
  RealColumn get progress => real().withDefault(const Constant(0))();
}
