import 'package:drift/drift.dart';

import 'syncable_columns.dart';

class Friendships extends Table with SyncableColumns {
  TextColumn get requesterId => text()();
  TextColumn get addresseeId => text()();
  TextColumn get status => text()();
  DateTimeColumn get respondedAt => dateTime().nullable()();
}
