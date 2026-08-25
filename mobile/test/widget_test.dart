import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:discgolf_tracker/main.dart';

void main() {
  testWidgets('app builds without error', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: DiscGolfTrackerApp()),
    );
    await tester.pumpAndSettle();

    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
