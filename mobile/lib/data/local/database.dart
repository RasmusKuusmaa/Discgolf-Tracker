import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'tables/achievements_table.dart';
import 'tables/courses_table.dart';
import 'tables/friendships_table.dart';
import 'tables/hole_scores_table.dart';
import 'tables/holes_table.dart';
import 'tables/layouts_table.dart';
import 'tables/round_players_table.dart';
import 'tables/rounds_table.dart';
import 'tables/user_layout_stats_table.dart';

part 'database.g.dart';

@DriftDatabase(
  tables: [
    Courses,
    Layouts,
    Holes,
    Rounds,
    RoundPlayers,
    HoleScores,
    Friendships,
    Achievements,
    UserLayoutStats,
  ],
)
class AppDatabase extends _$AppDatabase {
  AppDatabase([QueryExecutor? executor]) : super(executor ?? _openConnection());

  @override
  int get schemaVersion => 1;

  static LazyDatabase _openConnection() {
    return LazyDatabase(() async {
      final Directory directory = await getApplicationDocumentsDirectory();
      final File file = File(p.join(directory.path, 'discgolf_tracker.sqlite'));
      return NativeDatabase.createInBackground(file);
    });
  }
}
