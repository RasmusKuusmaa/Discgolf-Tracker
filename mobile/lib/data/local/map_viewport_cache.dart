import 'package:shared_preferences/shared_preferences.dart';

class CachedViewport {
  const CachedViewport({
    required this.lat,
    required this.lng,
    required this.zoom,
  });

  final double lat;
  final double lng;
  final double zoom;
}

const String _latKey = 'map_viewport_lat';
const String _lngKey = 'map_viewport_lng';
const String _zoomKey = 'map_viewport_zoom';

/// Persists the last map viewport the user looked at, so reopening the map
/// screen offline — with no fresh GPS fix and no network — still centers on
/// somewhere useful instead of the whole-world default view.
class MapViewportCache {
  Future<CachedViewport?> load() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    final double? lat = prefs.getDouble(_latKey);
    final double? lng = prefs.getDouble(_lngKey);
    final double? zoom = prefs.getDouble(_zoomKey);
    if (lat == null || lng == null || zoom == null) {
      return null;
    }
    return CachedViewport(lat: lat, lng: lng, zoom: zoom);
  }

  Future<void> save({
    required double lat,
    required double lng,
    required double zoom,
  }) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_latKey, lat);
    await prefs.setDouble(_lngKey, lng);
    await prefs.setDouble(_zoomKey, zoom);
  }
}
