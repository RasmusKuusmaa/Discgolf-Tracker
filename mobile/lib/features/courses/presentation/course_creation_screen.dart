import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import '../../../core/location/location_permission_flow.dart';
import '../providers/course_creation_controller.dart';
import '../providers/course_creation_state.dart';
import '../providers/hole_draft.dart';

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
        child: switch (state.currentStep) {
          0 => const _BasicsStep(),
          1 => const _LayoutStep(),
          2 => const _HolesStep(),
          _ => const Center(child: Text('Review coming soon')),
        },
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

class _LayoutStep extends ConsumerStatefulWidget {
  const _LayoutStep();

  @override
  ConsumerState<_LayoutStep> createState() => _LayoutStepState();
}

class _LayoutStepState extends ConsumerState<_LayoutStep> {
  late final TextEditingController _nameController = TextEditingController(
    text: ref.read(courseCreationControllerProvider).layoutName,
  );

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  void _sync({String? layoutName, int? holeCount}) {
    final CourseCreationState current = ref.read(
      courseCreationControllerProvider,
    );
    ref
        .read(courseCreationControllerProvider.notifier)
        .updateLayout(
          layoutName: layoutName ?? current.layoutName,
          holeCount: holeCount ?? current.holeCount,
        );
  }

  @override
  Widget build(BuildContext context) {
    final CourseCreationState state = ref.watch(
      courseCreationControllerProvider,
    );
    final TextTheme textTheme = Theme.of(context).textTheme;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        TextField(
          controller: _nameController,
          onChanged: (value) => _sync(layoutName: value),
          decoration: const InputDecoration(labelText: 'Layout name'),
        ),
        const SizedBox(height: 24),
        Text('Number of holes', style: textTheme.titleSmall),
        const SizedBox(height: 8),
        Row(
          children: [
            IconButton.outlined(
              onPressed: state.holeCount > minHoleCount
                  ? () => _sync(holeCount: state.holeCount - 1)
                  : null,
              icon: const Icon(Icons.remove),
            ),
            Expanded(
              child: Text(
                '${state.holeCount}',
                textAlign: TextAlign.center,
                style: textTheme.headlineSmall,
              ),
            ),
            IconButton.outlined(
              onPressed: state.holeCount < maxHoleCount
                  ? () => _sync(holeCount: state.holeCount + 1)
                  : null,
              icon: const Icon(Icons.add),
            ),
          ],
        ),
        const SizedBox(height: 24),
        Row(
          children: [
            TextButton(
              onPressed: () =>
                  ref.read(courseCreationControllerProvider.notifier).goBack(),
              child: const Text('Back'),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton(
                onPressed: state.canLeaveLayoutStep
                    ? () => ref
                          .read(courseCreationControllerProvider.notifier)
                          .completeLayoutStep()
                    : null,
                child: const Text('Next: Holes'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _HolesStep extends ConsumerWidget {
  const _HolesStep();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final CourseCreationState state = ref.watch(
      courseCreationControllerProvider,
    );

    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            itemCount: state.holes.length,
            itemBuilder: (context, index) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _HoleEditorCard(hole: state.holes[index]),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: Row(
            children: [
              TextButton(
                onPressed: () => ref
                    .read(courseCreationControllerProvider.notifier)
                    .goBack(),
                child: const Text('Back'),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton(
                  onPressed: () => ref
                      .read(courseCreationControllerProvider.notifier)
                      .completeHolesStep(),
                  child: const Text('Next: Review'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _HoleEditorCard extends ConsumerStatefulWidget {
  const _HoleEditorCard({required this.hole});

  final HoleDraft hole;

  @override
  ConsumerState<_HoleEditorCard> createState() => _HoleEditorCardState();
}

class _HoleEditorCardState extends ConsumerState<_HoleEditorCard> {
  late final TextEditingController _distanceController = TextEditingController(
    text: _formatDistance(widget.hole.distanceM),
  );
  final FocusNode _distanceFocusNode = FocusNode();
  bool _isCapturingTee = false;
  bool _isCapturingBasket = false;

  static String _formatDistance(double? distanceM) =>
      distanceM == null ? '' : distanceM.round().toString();

  @override
  void didUpdateWidget(_HoleEditorCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    // GPS capture can auto-fill the distance while the field isn't focused;
    // don't touch the text while the user is actively typing in it.
    if (!_distanceFocusNode.hasFocus &&
        oldWidget.hole.distanceM != widget.hole.distanceM) {
      _distanceController.text = _formatDistance(widget.hole.distanceM);
    }
  }

  @override
  void dispose() {
    _distanceController.dispose();
    _distanceFocusNode.dispose();
    super.dispose();
  }

  Future<void> _capture({required bool isTee}) async {
    setState(() {
      if (isTee) {
        _isCapturingTee = true;
      } else {
        _isCapturingBasket = true;
      }
    });
    final bool granted = await ensureLocationPermission(
      context,
      rationale:
          'Allow location access to capture GPS coordinates for this hole.',
    );
    if (granted) {
      try {
        final Position position = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.best,
          ),
        );
        final CourseCreationController controller = ref.read(
          courseCreationControllerProvider.notifier,
        );
        if (isTee) {
          controller.captureTee(
            widget.hole.number,
            latitude: position.latitude,
            longitude: position.longitude,
            accuracyM: position.accuracy,
          );
        } else {
          controller.captureBasket(
            widget.hole.number,
            latitude: position.latitude,
            longitude: position.longitude,
            accuracyM: position.accuracy,
          );
        }
      } catch (_) {
        // No GPS fix available — the hole just stays uncaptured.
      }
    }
    if (mounted) {
      setState(() {
        _isCapturingTee = false;
        _isCapturingBasket = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final CourseCreationController controller = ref.read(
      courseCreationControllerProvider.notifier,
    );
    final TextTheme textTheme = Theme.of(context).textTheme;

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Hole ${widget.hole.number}', style: textTheme.titleMedium),
            const SizedBox(height: 12),
            Row(
              children: [
                Text('Par', style: textTheme.bodyMedium),
                const Spacer(),
                IconButton.outlined(
                  onPressed: widget.hole.par > 1
                      ? () => controller.updateHolePar(
                          widget.hole.number,
                          widget.hole.par - 1,
                        )
                      : null,
                  icon: const Icon(Icons.remove),
                ),
                SizedBox(
                  width: 32,
                  child: Text(
                    '${widget.hole.par}',
                    textAlign: TextAlign.center,
                    style: textTheme.titleMedium,
                  ),
                ),
                IconButton.outlined(
                  onPressed: widget.hole.par < 10
                      ? () => controller.updateHolePar(
                          widget.hole.number,
                          widget.hole.par + 1,
                        )
                      : null,
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _distanceController,
              focusNode: _distanceFocusNode,
              keyboardType: TextInputType.number,
              onChanged: (value) => controller.updateHoleDistance(
                widget.hole.number,
                double.tryParse(value),
              ),
              decoration: const InputDecoration(
                labelText: 'Distance (m)',
                helperText:
                    'Auto-filled once tee and basket are captured — edit to override',
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _CaptureButton(
                    label: 'Capture tee',
                    isCaptured: widget.hole.hasTee,
                    accuracyM: widget.hole.teeAccuracyM,
                    isLoading: _isCapturingTee,
                    onPressed: () => _capture(isTee: true),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _CaptureButton(
                    label: 'Capture basket',
                    isCaptured: widget.hole.hasBasket,
                    accuracyM: widget.hole.basketAccuracyM,
                    isLoading: _isCapturingBasket,
                    onPressed: () => _capture(isTee: false),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _CaptureButton extends StatelessWidget {
  const _CaptureButton({
    required this.label,
    required this.isCaptured,
    required this.accuracyM,
    required this.isLoading,
    required this.onPressed,
  });

  final String label;
  final bool isCaptured;
  final double? accuracyM;
  final bool isLoading;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        OutlinedButton.icon(
          onPressed: isLoading ? null : onPressed,
          icon: isLoading
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Icon(
                  isCaptured ? Icons.check_circle : Icons.gps_fixed,
                  size: 16,
                ),
          label: Text(label, style: Theme.of(context).textTheme.labelMedium),
        ),
        if (isCaptured)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              accuracyM == null
                  ? 'Captured'
                  : 'Captured · ±${accuracyM!.round()} m',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.labelSmall
                  ?.copyWith(color: colorScheme.onSurfaceVariant),
            ),
          ),
      ],
    );
  }
}
