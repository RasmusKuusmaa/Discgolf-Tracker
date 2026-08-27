import 'package:drift/drift.dart';

import 'syncable_columns.dart';

class Holes extends Table with SyncableColumns {
  TextColumn get layoutId => text()();
  IntColumn get number => integer()();
  IntColumn get par => integer()();
  RealColumn get distanceM => real().nullable()();
  RealColumn get teeLatitude => real().nullable()();
  RealColumn get teeLongitude => real().nullable()();
  RealColumn get basketLatitude => real().nullable()();
  RealColumn get basketLongitude => real().nullable()();
  RealColumn get elevationDeltaM => real().nullable()();
  TextColumn get notes => text().nullable()();
}
