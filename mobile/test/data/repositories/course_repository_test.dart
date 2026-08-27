import 'package:dio/dio.dart';
import 'package:discgolf_tracker/data/local/database.dart';
import 'package:discgolf_tracker/data/local/mutation_queue_repository.dart';
import 'package:discgolf_tracker/data/remote/courses_api.dart';
import 'package:discgolf_tracker/data/repositories/course_repository.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

const Map<String, dynamic> _pineHollowJson = {
  'id': 'course-1',
  'name': 'Pine Hollow',
  'slug': 'pine-hollow',
  'description': 'A wooded 18-hole course.',
  'city': 'Springfield',
  'region': null,
  'country': 'US',
  'location': {'lat': 40.0, 'lng': -83.0},
  'created_by_id': 'user-1',
  'visibility': 'public',
  'status': 'published',
  'is_verified': true,
  'layouts': [
    {
      'id': 'layout-1',
      'name': 'Long tees',
      'hole_count': 1,
      'par_total': 3,
      'total_distance_m': 90.0,
      'difficulty': 'intermediate',
      'is_default': true,
      'is_active': true,
      'holes': [
        {
          'id': 'hole-1',
          'number': 1,
          'par': 3,
          'distance_m': 90.0,
          'tee_location': {'lat': 40.001, 'lng': -83.001},
          'basket_location': {'lat': 40.002, 'lng': -83.002},
          'elevation_delta_m': null,
          'notes': null,
        },
      ],
    },
  ],
};

const Map<String, dynamic> _farAwayJson = {
  'id': 'course-2',
  'name': 'Distant Course',
  'slug': 'distant-course',
  'description': null,
  'city': null,
  'region': null,
  'country': 'AU',
  'location': {'lat': -33.0, 'lng': 151.0},
  'visibility': 'public',
  'status': 'published',
  'is_verified': false,
  'layouts': <dynamic>[],
};

void main() {
  late AppDatabase db;
  late CourseRepository repository;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    final adapter = FakeHttpClientAdapter({
      'GET /courses': (options) => FakeHttpClientAdapter.json({
        'items': [_pineHollowJson, _farAwayJson],
      }, 200),
    });
    final Dio dio = Dio()..httpClientAdapter = adapter;
    repository = CourseRepository(db, MutationQueueRepository(db), CoursesApi(dio));
  });

  tearDown(() => db.close());

  test('refreshList caches courses with nested layouts and holes', () async {
    await repository.refreshList();

    final all = await repository.all();
    expect(all, hasLength(2));

    final pineHollow = all.firstWhere((c) => c.id == 'course-1');
    expect(pineHollow.name, 'Pine Hollow');
    expect(pineHollow.layouts, hasLength(1));
    expect(pineHollow.layouts.single.holes, hasLength(1));
    expect(pineHollow.layouts.single.holes.single.par, 3);
  });

  test('byId reads a single cached course', () async {
    await repository.refreshList();

    final course = await repository.byId('course-2');

    expect(course, isNotNull);
    expect(course!.name, 'Distant Course');
  });

  test('search matches by name or city, case-insensitively', () async {
    await repository.refreshList();

    expect((await repository.search('pine')).map((c) => c.id), ['course-1']);
    expect((await repository.search('springfield')).map((c) => c.id), ['course-1']);
    expect(await repository.search('nonexistent'), isEmpty);
  });

  test('nearby filters by haversine distance and sorts nearest first', () async {
    await repository.refreshList();

    final results = await repository.nearby(lat: 40.0, lng: -83.0, radiusKm: 10);

    expect(results.map((c) => c.id), ['course-1']);
  });
}
