import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import '../../../core/location/location_permission_flow.dart';
import '../providers/course_creation_controller.dart';
import '../providers/course_creation_state.dart';

const LatLng _defaultMapCenter = LatLng(20, 0);
const double _defaultMapZoom = 2;
const double _pickedMapZoom = 14;

class CourseCreationScreen extends ConsumerWidget {
  const CourseCreationScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final CourseCreationState state = ref.watch(
      courseCreationControllerProvider,
    );

    return Scaffold(
      appBar: AppBar(title: const Text('New course')),
      body: SafeArea(
        child: state.currentStep == 0
            ? const _BasicsStep()
            : const Center(child: Text('Layout setup coming soon')),
      ),
    );
  }
}

class _BasicsStep extends ConsumerStatefulWidget {
  const _BasicsStep();

  @override
  ConsumerState<_BasicsStep> createState() => _BasicsStepState();
}

class _BasicsStepState extends ConsumerState<_BasicsStep> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _cityController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();
  final MapController _mapController = MapController();
  bool _isLocating = false;

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _cityController.dispose();
    _countryController.dispose();
    super.dispose();
  }

  void _syncBasics() {
    ref
        .read(courseCreationControllerProvider.notifier)
        .updateBasics(
          name: _nameController.text,
          description: _descriptionController.text.trim().isEmpty
              ? null
              : _descriptionController.text.trim(),
          city: _cityController.text.trim().isEmpty
              ? null
              : _cityController.text.trim(),
          country: _countryController.text.trim().isEmpty
              ? null
              : _countryController.text.trim(),
        );
  }

  Future<void> _useMyLocation() async {
    setState(() => _isLocating = true);
    final bool granted = await ensureLocationPermission(
      context,
      rationale:
          'Allow location access to set this course\'s location automatically.',
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
          accuracy: LocationAccuracy.high,
        ),
      );
      if (!mounted) {
        return;
      }
      final LatLng point = LatLng(position.latitude, position.longitude);
      ref
          .read(courseCreationControllerProvider.notifier)
          .setLocation(point.latitude, point.longitude);
      _mapController.move(point, _pickedMapZoom);
    } catch (_) {
      // Location unavailable — the user can still tap the map to pick one.
    } finally {
      if (mounted) {
        setState(() => _isLocating = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final CourseCreationState state = ref.watch(
      courseCreationControllerProvider,
    );
    final TextTheme textTheme = Theme.of(context).textTheme;
    final ColorScheme colorScheme = Theme.of(context).colorScheme;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        TextField(
          controller: _nameController,
          onChanged: (_) => _syncBasics(),
          decoration: const InputDecoration(labelText: 'Course name'),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _descriptionController,
          onChanged: (_) => _syncBasics(),
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Description (optional)',
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _cityController,
                onChanged: (_) => _syncBasics(),
                decoration: const InputDecoration(labelText: 'City'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextField(
                controller: _countryController,
                onChanged: (_) => _syncBasics(),
                decoration: const InputDecoration(labelText: 'Country'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),
        Text('Location', style: textTheme.titleSmall),
        const SizedBox(height: 4),
        Text(
          state.hasLocation
              ? '${state.latitude!.toStringAsFixed(5)}, ${state.longitude!.toStringAsFixed(5)}'
              : 'Tap the map to drop a pin, or use your current location.',
          style: textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: SizedBox(
            height: 220,
            child: FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: state.hasLocation
                    ? LatLng(state.latitude!, state.longitude!)
                    : _defaultMapCenter,
                initialZoom: state.hasLocation
                    ? _pickedMapZoom
                    : _defaultMapZoom,
                onTap: (tapPosition, point) => ref
                    .read(courseCreationControllerProvider.notifier)
                    .setLocation(point.latitude, point.longitude),
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.discgolftracker.discgolf_tracker',
                ),
                if (state.hasLocation)
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: LatLng(state.latitude!, state.longitude!),
                        width: 32,
                        height: 32,
                        child: Icon(
                          Icons.location_on,
                          color: colorScheme.primary,
                          size: 32,
                        ),
                      ),
                    ],
                  ),
                const SimpleAttributionWidget(
                  source: Text('OpenStreetMap contributors'),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: _isLocating ? null : _useMyLocation,
          icon: _isLocating
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.my_location),
          label: const Text('Use my location'),
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: state.canLeaveBasicsStep
                ? () => ref
                      .read(courseCreationControllerProvider.notifier)
                      .completeBasicsStep()
                : null,
            child: const Text('Next: Layout'),
          ),
        ),
      ],
    );
  }
}
