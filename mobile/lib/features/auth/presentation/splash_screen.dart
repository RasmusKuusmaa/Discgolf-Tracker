import 'package:flutter/material.dart';

import '../../../core/widgets/loading_indicator.dart';

/// Shown while [AuthController] restores (or fails to restore) the
/// session on launch; the router redirects away as soon as that resolves.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: LoadingIndicator(),
    );
  }
}
