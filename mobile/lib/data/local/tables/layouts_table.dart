import 'package:drift/drift.dart';

import 'syncable_columns.dart';

class Layouts extends Table with SyncableColumns {
  TextColumn get courseId => text()();
  TextColumn get name => text()();
  IntColumn get holeCount => integer().withDefault(const Constant(0))();
  IntColumn get parTotal => integer().withDefault(const Constant(0))();
  RealColumn get totalDistanceM => real().nullable()();
  TextColumn get difficulty => text().nullable()();
  BoolColumn get isDefault => boolean().withDefault(const Constant(false))();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();
}
