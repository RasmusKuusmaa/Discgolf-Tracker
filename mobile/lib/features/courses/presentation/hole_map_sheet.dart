import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../../domain/models/hole.dart';

/// Bottom sheet content showing a hole's tee and basket on a small map,
/// connected by a line, alongside its distance. Only meaningful for holes
/// that have both coordinates captured.
class HoleMapSheet extends StatelessWidget {
  const HoleMapSheet({super.key, required this.hole});

  final Hole hole;

  @override
  Widget build(BuildContext context) {
    final LatLng tee = LatLng(hole.teeLatitude!, hole.teeLongitude!);
    final LatLng basket = LatLng(hole.basketLatitude!, hole.basketLongitude!);
    final TextTheme textTheme = Theme.of(context).textTheme;
    final ColorScheme colorScheme = Theme.of(context).colorScheme;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Hole ${hole.number}', style: textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              hole.distanceM == null
                  ? 'Par ${hole.par}'
                  : 'Par ${hole.par} · ${hole.distanceM!.round()} m',
              style: textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 260,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: FlutterMap(
                  options: MapOptions(
                    initialCameraFit: CameraFit.coordinates(
                      coordinates: [tee, basket],
                      padding: const EdgeInsets.all(48),
                    ),
                    interactionOptions: const InteractionOptions(
                      flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag,
                    ),
                  ),
                  children: [
                    TileLayer(
                      urlTemplate:
                          'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName:
                          'com.discgolftracker.discgolf_tracker',
                    ),
                    PolylineLayer(
                      polylines: [
                        Polyline(
                          points: [tee, basket],
                          color: colorScheme.primary,
                          strokeWidth: 3,
                        ),
                      ],
                    ),
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: tee,
                          width: 28,
                          height: 28,
                          child: Icon(
                            Icons.golf_course,
                            color: colorScheme.primary,
                          ),
                        ),
                        Marker(
                          point: basket,
                          width: 28,
                          height: 28,
                          child: const Icon(
                            Icons.circle,
                            color: Colors.orange,
                            size: 18,
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
          ],
        ),
      ),
    );
  }
}
