import 'package:drift/drift.dart';

/// Columns present on every syncable table: a client-generated UUIDv7 [id],
/// server timestamps, and [isDirty] marking rows with unsynced local writes.
mixin SyncableColumns on Table {
  TextColumn get id => text()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();
  DateTimeColumn get deletedAt => dateTime().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
