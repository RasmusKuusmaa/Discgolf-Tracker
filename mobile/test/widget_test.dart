import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:discgolf_tracker/core/network/network_providers.dart';
import 'package:discgolf_tracker/data/local/token_store.dart';
import 'package:discgolf_tracker/domain/models/auth_tokens.dart';
import 'package:discgolf_tracker/features/auth/presentation/login_screen.dart';
import 'package:discgolf_tracker/main.dart';

class _FakeTokenStore implements TokenStore {
  @override
  Future<AuthTokens?> readTokens() async => null;

  @override
  Future<void> saveTokens(AuthTokens tokens) async {}

  @override
  Future<void> clearTokens() async {}
}

void main() {
  testWidgets('boots to the login screen when unauthenticated', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [tokenStoreProvider.overrideWithValue(_FakeTokenStore())],
        child: const DiscGolfTrackerApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(LoginScreen), findsOneWidget);
  });
}
