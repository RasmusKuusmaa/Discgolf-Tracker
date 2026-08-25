import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';

void main() {
  runApp(const DiscGolfTrackerApp());
}

class DiscGolfTrackerApp extends StatelessWidget {
  const DiscGolfTrackerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Disc Golf Tracker',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      home: const Placeholder(),
    );
  }
}
