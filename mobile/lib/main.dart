import 'package:flutter/material.dart';

void main() {
  runApp(const DiscGolfTrackerApp());
}

class DiscGolfTrackerApp extends StatelessWidget {
  const DiscGolfTrackerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Disc Golf Tracker',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
      ),
      home: const Placeholder(),
    );
  }
}
