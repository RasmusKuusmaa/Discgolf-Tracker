import '../../core/ids/uuid7.dart';
import 'database.dart';

enum MutationOperation { create, update, delete }

/// Records local writes as `MutationQueue` rows so a later sync pass can
/// push them — the path every repository's writes go through alongside
/// its own Drift table write.
class MutationQueueRepository {
  MutationQueueRepository(this._db);

  final AppDatabase _db;

  Future<void> enqueue({
    required String entityType,
    required String entityId,
    required MutationOperation operation,
    required String payloadJson,
  }) {
    return _db
        .into(_db.mutationQueue)
        .insert(
          MutationQueueCompanion.insert(
            id: generateId(),
            entityType: entityType,
            entityId: entityId,
            operation: operation.name,
            payload: payloadJson,
            createdAt: DateTime.now().toUtc(),
          ),
        );
  }
}
