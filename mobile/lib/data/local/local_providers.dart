import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/network_providers.dart';
import '../repositories/course_repository.dart';
import 'database.dart';
import 'map_viewport_cache.dart';
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

final Provider<MapViewportCache> mapViewportCacheProvider =
    Provider<MapViewportCache>((ref) {
      return MapViewportCache();
    });

final Provider<CourseRepository> courseRepositoryProvider =
    Provider<CourseRepository>((ref) {
      return CourseRepository(
        ref.watch(appDatabaseProvider),
        ref.watch(mutationQueueRepositoryProvider),
        ref.watch(coursesApiProvider),
      );
    });
