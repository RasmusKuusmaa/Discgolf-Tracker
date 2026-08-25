import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:discgolf_tracker/features/auth/presentation/login_screen.dart';
import 'package:discgolf_tracker/main.dart';

void main() {
  testWidgets('boots to the login screen when unauthenticated', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const ProviderScope(child: DiscGolfTrackerApp()),
    );
    await tester.pumpAndSettle();

    expect(find.byType(LoginScreen), findsOneWidget);
  });
}
