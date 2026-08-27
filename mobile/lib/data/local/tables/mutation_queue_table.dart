import 'package:drift/drift.dart';

/// A pending local write waiting to be pushed to the server. [id] doubles
/// as the `mutation_id` sent to `/sync/push` for idempotent replay.
class MutationQueue extends Table {
  TextColumn get id => text()();
  TextColumn get entityType => text()();
  TextColumn get entityId => text()();
  TextColumn get operation => text()();
  TextColumn get payload => text()();
  DateTimeColumn get createdAt => dateTime()();
  IntColumn get attempts => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}
