import 'package:drift/drift.dart';

import 'syncable_columns.dart';

class Rounds extends Table with SyncableColumns {
  TextColumn get layoutId => text()();
  TextColumn get createdById => text()();
  DateTimeColumn get startedAt => dateTime()();
  DateTimeColumn get completedAt => dateTime().nullable()();
  TextColumn get status => text()();
  BoolColumn get isPractice => boolean().withDefault(const Constant(false))();
  TextColumn get weatherNote => text().nullable()();
  BoolColumn get clientGenerated => boolean().withDefault(const Constant(false))();
  BoolColumn get isPartial => boolean().withDefault(const Constant(false))();
}
