import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_marker_cluster/flutter_map_marker_cluster.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';

import '../../../core/location/location_permission_flow.dart';
import '../../../data/local/local_providers.dart';
import '../../../data/local/map_viewport_cache.dart';
import '../../../domain/models/course.dart';
import '../../../domain/models/layout.dart';

const LatLng _fallbackCenter = LatLng(20, 0);
const double _fallbackZoom = 2;
const double _locatedZoom = 14;
const Duration _viewportDebounce = Duration(milliseconds: 600);

class CourseMapScreen extends ConsumerStatefulWidget {
  const CourseMapScreen({super.key});

  @override
  ConsumerState<CourseMapScreen> createState() => _CourseMapScreenState();
}

class _CourseMapScreenState extends ConsumerState<CourseMapScreen> {
  final MapController _mapController = MapController();
  LatLng? _currentLocation;
  bool _isLocating = true;
  List<Course> _courses = <Course>[];
  Timer? _viewportDebounceTimer;

  @override
  void initState() {
    super.initState();
    unawaited(_restoreViewport());
    unawaited(_locate());
    unawaited(_loadCourses());
  }

  Future<void> _restoreViewport() async {
    final CachedViewport? cached = await ref
        .read(mapViewportCacheProvider)
        .load();
    if (cached != null && mounted) {
      _mapController.move(LatLng(cached.lat, cached.lng), cached.zoom);
    }
  }

  @override
  void dispose() {
    _viewportDebounceTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadCourses() async {
    final List<Course> courses = await ref.read(courseRepositoryProvider).all();
    if (mounted) {
      setState(() => _courses = courses);
    }
  }

  void _onMapPositionChanged() {
    _viewportDebounceTimer?.cancel();
    _viewportDebounceTimer = Timer(_viewportDebounce, _onViewportSettled);
  }

  Future<void> _onViewportSettled() async {
    final LatLng center = _mapController.camera.center;
    unawaited(
      ref
          .read(mapViewportCacheProvider)
          .save(
            lat: center.latitude,
            lng: center.longitude,
            zoom: _mapController.camera.zoom,
          ),
    );
    await _refreshViewportCourses();
  }

  Future<void> _refreshViewportCourses() async {
    final LatLngBounds bounds = _mapController.camera.visibleBounds;
    try {
      final List<Course> courses = await ref
          .read(courseRepositoryProvider)
          .refreshByBbox(
            minLat: bounds.south,
            minLng: bounds.west,
            maxLat: bounds.north,
            maxLng: bounds.east,
          );
      if (mounted) {
        setState(() => _courses = courses);
      }
    } catch (_) {
      // Offline or the server is unreachable — keep showing what's cached.
    }
  }

  Future<void> _locate() async {
    setState(() => _isLocating = true);
    final bool granted = await ensureLocationPermission(
      context,
      rationale:
          'Allow location access to show where you are on the course map.',
    );
    if (!granted) {
      if (mounted) {
        setState(() => _isLocating = false);
      }
      return;
    }
    try {
      final Position position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
        ),
      );
      final LatLng location = LatLng(position.latitude, position.longitude);
      if (!mounted) {
        return;
      }
      setState(() {
        _currentLocation = location;
        _isLocating = false;
      });
      _mapController.move(location, _locatedZoom);
    } catch (_) {
      // No location available — the map just stays at the world view.
      if (mounted) {
        setState(() => _isLocating = false);
      }
    }
  }

  void _showCoursePreview(Course course) {
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => _CoursePreviewSheet(course: course),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Map')),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: _fallbackCenter,
              initialZoom: _fallbackZoom,
              onPositionChanged: (camera, hasGesture) =>
                  _onMapPositionChanged(),
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.discgolftracker.discgolf_tracker',
              ),
              MarkerClusterLayerWidget(
                options: MarkerClusterLayerOptions(
                  maxClusterRadius: 60,
                  size: const Size(36, 36),
                  markerChildBehavior: true,
                  markers: [
                    for (final Course course in _courses)
                      Marker(
                        point: LatLng(course.latitude, course.longitude),
                        width: 36,
                        height: 36,
                        child: _CourseMarkerPin(
                          onTap: () => _showCoursePreview(course),
                        ),
                      ),
                  ],
                  builder: (context, markers) =>
                      _ClusterBadge(count: markers.length),
                ),
              ),
              if (_currentLocation != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: _currentLocation!,
                      width: 22,
                      height: 22,
                      child: const _CurrentLocationDot(),
                    ),
                  ],
                ),
              const SimpleAttributionWidget(
                source: Text('OpenStreetMap contributors'),
              ),
            ],
          ),
          if (_isLocating)
            const Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: LinearProgressIndicator(),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _locate,
        tooltip: 'Find my location',
        child: const Icon(Icons.my_location),
      ),
    );
  }
}

class _CurrentLocationDot extends StatelessWidget {
  const _CurrentLocationDot();

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: colorScheme.primary,
        border: Border.all(color: Colors.white, width: 2),
        boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
      ),
    );
  }
}

class _CourseMarkerPin extends StatelessWidget {
  const _CourseMarkerPin({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return GestureDetector(
      onTap: onTap,
      child: Icon(
        Icons.location_on,
        color: colorScheme.primary,
        size: 36,
        shadows: const [Shadow(color: Colors.black38, blurRadius: 3)],
      ),
    );
  }
}

class _ClusterBadge extends StatelessWidget {
  const _ClusterBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: colorScheme.primary,
        border: Border.all(color: Colors.white, width: 2),
      ),
      alignment: Alignment.center,
      child: Text(
        '$count',
        style: Theme.of(context).textTheme.labelMedium
            ?.copyWith(color: colorScheme.onPrimary),
      ),
    );
  }
}

class _CoursePreviewSheet extends StatelessWidget {
  const _CoursePreviewSheet({required this.course});

  final Course course;

  @override
  Widget build(BuildContext context) {
    final TextTheme textTheme = Theme.of(context).textTheme;
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    final String location = [
      course.city,
      course.country,
    ].where((part) => part != null && part.isNotEmpty).join(', ');
    final Layout? layout = course.layouts.isEmpty
        ? null
        : course.layouts.firstWhere(
            (candidate) => candidate.isDefault,
            orElse: () => course.layouts.first,
          );

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(course.name, style: textTheme.titleLarge),
            if (location.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                location,
                style: textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
            if (layout != null) ...[
              const SizedBox(height: 8),
              Text(
                '${layout.holeCount} holes · Par ${layout.parTotal}',
                style: textTheme.bodyMedium,
              ),
            ],
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  context.push('/courses/${course.id}');
                },
                child: const Text('View course'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
