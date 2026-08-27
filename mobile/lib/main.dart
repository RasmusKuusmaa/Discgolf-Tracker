import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/router/app_router.dart';
import 'core/router/auth_state.dart';
import 'core/theme/app_theme.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return buildAppRouter(ref.watch(routerAuthNotifierProvider));
});

void main() {
  runApp(const ProviderScope(child: DiscGolfTrackerApp()));
}

class DiscGolfTrackerApp extends ConsumerWidget {
  const DiscGolfTrackerApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'Disc Golf Tracker',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
