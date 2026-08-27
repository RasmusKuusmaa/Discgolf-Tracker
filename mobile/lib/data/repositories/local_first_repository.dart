import '../local/database.dart';
import '../local/mutation_queue_repository.dart';

/// Base for every feature repository (courses, rounds, friends, ...):
/// reads come from [db] alone, writes go to [db] and [mutationQueue]
/// together, and the network is never touched from the UI path — a
/// `SyncService` (Phase 18) drains [mutationQueue] in the background.
abstract class LocalFirstRepository {
  LocalFirstRepository(this.db, this.mutationQueue);

  final AppDatabase db;
  final MutationQueueRepository mutationQueue;
}
