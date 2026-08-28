import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../widgets/confirmation_dialog.dart';

/// Requests location permission with a rationale shown up front, and
/// handles denial gracefully: a permanent denial or disabled location
/// service is pointed at system settings rather than silently failing or
/// re-prompting every time. Returns whether location is actually usable.
Future<bool> ensureLocationPermission(
  BuildContext context, {
  String rationale =
      'Allow location access to sort courses by distance and find ones nearby.',
}) async {
  LocationPermission permission = await Geolocator.checkPermission();

  if (permission == LocationPermission.denied) {
    if (!context.mounted) {
      return false;
    }
    final bool proceed = await showConfirmationDialog(
      context,
      title: 'Location access',
      message: rationale,
      confirmText: 'Allow',
      cancelText: 'Not now',
    );
    if (!proceed) {
      return false;
    }
    permission = await Geolocator.requestPermission();
  }

  if (permission == LocationPermission.deniedForever) {
    if (!context.mounted) {
      return false;
    }
    final bool openSettings = await showConfirmationDialog(
      context,
      title: 'Location access needed',
      message:
          '$rationale You previously denied this — enable it from system settings to use it.',
      confirmText: 'Open settings',
      cancelText: 'Not now',
    );
    if (openSettings) {
      await Geolocator.openAppSettings();
    }
    return false;
  }

  if (permission != LocationPermission.whileInUse &&
      permission != LocationPermission.always) {
    return false;
  }

  if (await Geolocator.isLocationServiceEnabled()) {
    return true;
  }
  if (!context.mounted) {
    return false;
  }
  final bool openLocationSettings = await showConfirmationDialog(
    context,
    title: 'Location services are off',
    message:
        'Turn on location services to use distance sort and nearby search.',
    confirmText: 'Open settings',
    cancelText: 'Not now',
  );
  if (openLocationSettings) {
    await Geolocator.openLocationSettings();
  }
  return false;
}
