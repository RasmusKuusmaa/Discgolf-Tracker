import 'dart:math' as math;

/// Great-circle distance between two coordinates, in kilometers.
double haversineKm(double lat1, double lng1, double lat2, double lng2) {
  const double earthRadiusKm = 6371;
  final double dLat = _degToRad(lat2 - lat1);
  final double dLng = _degToRad(lng2 - lng1);
  final double a =
      math.sin(dLat / 2) * math.sin(dLat / 2) +
      math.cos(_degToRad(lat1)) *
          math.cos(_degToRad(lat2)) *
          math.sin(dLng / 2) *
          math.sin(dLng / 2);
  final double c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  return earthRadiusKm * c;
}

double _degToRad(double deg) => deg * (math.pi / 180);
