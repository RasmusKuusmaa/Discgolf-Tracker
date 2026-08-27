import 'package:drift/drift.dart';

import '../../core/geo/haversine.dart';
import '../../domain/models/course.dart';
import '../../domain/models/hole.dart';
import '../../domain/models/layout.dart';
import '../local/database.dart' as schema;
import '../remote/courses_api.dart';
import 'local_first_repository.dart';

/// Reads courses from the local cache; [refreshList], [refreshById] and
/// [refreshNearby] populate that cache from the server on demand — the UI
/// only ever calls the local query methods.
class CourseRepository extends LocalFirstRepository {
  CourseRepository(super.db, super.mutationQueue, this._coursesApi);

  final CoursesApi _coursesApi;

  Future<List<Course>> all() async {
    final List<schema.Course> rows = await db.select(db.courses).get();
    return Future.wait(rows.map(_courseFromRow));
  }

  Future<Course?> byId(String id) async {
    final schema.Course? row = await (db.select(
      db.courses,
    )..where((t) => t.id.equals(id))).getSingleOrNull();
    return row == null ? null : _courseFromRow(row);
  }

  Future<List<Course>> search(String query) async {
    final String pattern = '%${query.toLowerCase()}%';
    final List<schema.Course> rows = await (db.select(db.courses)
          ..where((t) => t.name.lower().like(pattern) | t.city.lower().like(pattern)))
        .get();
    return Future.wait(rows.map(_courseFromRow));
  }

  /// Distances are computed with the haversine formula over the local
  /// cache — no PostGIS locally, and the cache is small enough that this
  /// is cheap.
  Future<List<Course>> nearby({
    required double lat,
    required double lng,
    required double radiusKm,
  }) async {
    final List<schema.Course> rows = await db.select(db.courses).get();
    final List<(schema.Course, double)> withDistance =
        rows
            .map((row) => (row, haversineKm(lat, lng, row.latitude, row.longitude)))
            .where((entry) => entry.$2 <= radiusKm)
            .toList()
          ..sort((a, b) => a.$2.compareTo(b.$2));
    return Future.wait(withDistance.map((entry) => _courseFromRow(entry.$1)));
  }

  Future<List<Course>> refreshList({String? query, String? country}) async {
    final List<Course> courses = await _coursesApi.fetchList(query: query, country: country);
    await _cacheAll(courses);
    return courses;
  }

  Future<Course> refreshById(String id) async {
    final Course course = await _coursesApi.fetchById(id);
    await _cacheAll([course]);
    return course;
  }

  Future<List<Course>> refreshNearby({
    required double lat,
    required double lng,
    required double radiusKm,
  }) async {
    final List<Course> courses = await _coursesApi.fetchNearby(
      lat: lat,
      lng: lng,
      radiusKm: radiusKm,
    );
    await _cacheAll(courses);
    return courses;
  }

  Future<void> _cacheAll(List<Course> courses) {
    final DateTime now = DateTime.now().toUtc();
    return db.batch((batch) {
      for (final Course course in courses) {
        batch.insert(
          db.courses,
          schema.CoursesCompanion.insert(
            id: course.id,
            createdAt: now,
            updatedAt: now,
            name: course.name,
            slug: course.slug,
            description: Value(course.description),
            city: Value(course.city),
            region: Value(course.region),
            country: Value(course.country),
            latitude: course.latitude,
            longitude: course.longitude,
            createdById: Value(course.createdById),
            visibility: course.visibility,
            status: course.status,
            isVerified: Value(course.isVerified),
          ),
          mode: InsertMode.insertOrReplace,
        );
        for (final Layout layout in course.layouts) {
          batch.insert(
            db.layouts,
            schema.LayoutsCompanion.insert(
              id: layout.id,
              createdAt: now,
              updatedAt: now,
              courseId: layout.courseId,
              name: layout.name,
              holeCount: Value(layout.holeCount),
              parTotal: Value(layout.parTotal),
              totalDistanceM: Value(layout.totalDistanceM),
              difficulty: Value(layout.difficulty),
              isDefault: Value(layout.isDefault),
              isActive: Value(layout.isActive),
            ),
            mode: InsertMode.insertOrReplace,
          );
          for (final Hole hole in layout.holes) {
            batch.insert(
              db.holes,
              schema.HolesCompanion.insert(
                id: hole.id,
                createdAt: now,
                updatedAt: now,
                layoutId: hole.layoutId,
                number: hole.number,
                par: hole.par,
                distanceM: Value(hole.distanceM),
                teeLatitude: Value(hole.teeLatitude),
                teeLongitude: Value(hole.teeLongitude),
                basketLatitude: Value(hole.basketLatitude),
                basketLongitude: Value(hole.basketLongitude),
                elevationDeltaM: Value(hole.elevationDeltaM),
                notes: Value(hole.notes),
              ),
              mode: InsertMode.insertOrReplace,
            );
          }
        }
      }
    });
  }

  Future<Course> _courseFromRow(schema.Course row) async {
    final List<schema.Layout> layoutRows = await (db.select(
      db.layouts,
    )..where((t) => t.courseId.equals(row.id))).get();
    final List<Layout> layouts = await Future.wait(layoutRows.map(_layoutFromRow));
    return Course(
      id: row.id,
      name: row.name,
      slug: row.slug,
      description: row.description,
      city: row.city,
      region: row.region,
      country: row.country,
      latitude: row.latitude,
      longitude: row.longitude,
      createdById: row.createdById,
      visibility: row.visibility,
      status: row.status,
      isVerified: row.isVerified,
      layouts: layouts,
    );
  }

  Future<Layout> _layoutFromRow(schema.Layout row) async {
    final List<schema.Hole> holeRows = await (db.select(
      db.holes,
    )..where((t) => t.layoutId.equals(row.id))).get();
    return Layout(
      id: row.id,
      courseId: row.courseId,
      name: row.name,
      holeCount: row.holeCount,
      parTotal: row.parTotal,
      totalDistanceM: row.totalDistanceM,
      difficulty: row.difficulty,
      isDefault: row.isDefault,
      isActive: row.isActive,
      holes: holeRows.map(_holeFromRow).toList(),
    );
  }

  Hole _holeFromRow(schema.Hole row) {
    return Hole(
      id: row.id,
      layoutId: row.layoutId,
      number: row.number,
      par: row.par,
      distanceM: row.distanceM,
      teeLatitude: row.teeLatitude,
      teeLongitude: row.teeLongitude,
      basketLatitude: row.basketLatitude,
      basketLongitude: row.basketLongitude,
      elevationDeltaM: row.elevationDeltaM,
      notes: row.notes,
    );
  }
}
