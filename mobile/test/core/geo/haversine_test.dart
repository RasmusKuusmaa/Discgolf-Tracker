import 'package:discgolf_tracker/core/geo/haversine.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('same point is zero distance', () {
    expect(haversineKm(40.0, -83.0, 40.0, -83.0), closeTo(0, 0.0001));
  });

  test('matches a known distance within a small tolerance', () {
    // London to Paris is ~344km.
    final double km = haversineKm(51.5074, -0.1278, 48.8566, 2.3522);
    expect(km, closeTo(344, 5));
  });
}
