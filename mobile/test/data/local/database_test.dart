import 'package:discgolf_tracker/data/local/database.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppDatabase', () {
    late AppDatabase db;

    setUp(() => db = AppDatabase(NativeDatabase.memory()));
    tearDown(() => db.close());

    test('opens at the current schema version', () {
      expect(db.schemaVersion, 1);
    });

    test('onCreate migration creates every declared table', () async {
      final List<String> tableNames = (await db
              .customSelect(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
              )
              .get())
          .map((row) => row.read<String>('name'))
          .toList();

      expect(tableNames, containsAll(<String>[
        'courses',
        'layouts',
        'holes',
        'rounds',
        'round_players',
        'hole_scores',
        'friendships',
        'achievements',
        'user_layout_stats',
        'mutation_queue',
      ]));
    });
  });
}
