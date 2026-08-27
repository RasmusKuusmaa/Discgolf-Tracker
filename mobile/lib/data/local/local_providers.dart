import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'database.dart';
import 'mutation_queue_repository.dart';

final Provider<AppDatabase> appDatabaseProvider = Provider<AppDatabase>((ref) {
  final AppDatabase db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});

final Provider<MutationQueueRepository> mutationQueueRepositoryProvider =
    Provider<MutationQueueRepository>((ref) {
      return MutationQueueRepository(ref.watch(appDatabaseProvider));
    });
