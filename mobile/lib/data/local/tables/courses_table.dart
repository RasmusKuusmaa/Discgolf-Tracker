import 'package:drift/drift.dart';

import 'syncable_columns.dart';

class Courses extends Table with SyncableColumns {
  TextColumn get name => text()();
  TextColumn get slug => text()();
  TextColumn get description => text().nullable()();
  TextColumn get city => text().nullable()();
  TextColumn get region => text().nullable()();
  TextColumn get country => text().nullable()();
  RealColumn get latitude => real()();
  RealColumn get longitude => real()();
  TextColumn get createdById => text()();
  TextColumn get visibility => text()();
  TextColumn get status => text()();
  TextColumn get osmId => text().nullable()();
  BoolColumn get isVerified => boolean().withDefault(const Constant(false))();
}
