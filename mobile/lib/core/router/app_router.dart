import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/login_screen.dart';
import '../../features/courses/presentation/courses_screen.dart';
import '../../features/friends/presentation/friends_screen.dart';
import '../../features/play/presentation/play_screen.dart';
import '../../features/profile/presentation/profile_screen.dart';
import '../../features/stats/presentation/stats_screen.dart';
import 'app_shell.dart';
import 'auth_state.dart';

const _loginPath = '/login';
const _playPath = '/play';

GoRouter buildAppRouter(AuthState authState) {
  return GoRouter(
    initialLocation: _playPath,
    refreshListenable: authState,
    redirect: (context, state) {
      final isLoggingIn = state.matchedLocation == _loginPath;

      if (!authState.isAuthenticated && !isLoggingIn) {
        return _loginPath;
      }
      if (authState.isAuthenticated && isLoggingIn) {
        return _playPath;
      }
      return null;
    },
    routes: [
      GoRoute(
        path: _loginPath,
        builder: (context, state) => const LoginScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            AppShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: _playPath,
                builder: (context, state) => const PlayScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/courses',
                builder: (context, state) => const CoursesScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/stats',
                builder: (context, state) => const StatsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/friends',
                builder: (context, state) => const FriendsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                builder: (context, state) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
}
