import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/register_screen.dart';
import '../../features/auth/presentation/splash_screen.dart';
import '../../features/courses/presentation/course_creation_screen.dart';
import '../../features/courses/presentation/course_detail_screen.dart';
import '../../features/courses/presentation/course_map_screen.dart';
import '../../features/courses/presentation/courses_screen.dart';
import '../../features/friends/presentation/friends_screen.dart';
import '../../features/play/presentation/play_screen.dart';
import '../../features/profile/presentation/profile_screen.dart';
import '../../features/stats/presentation/stats_screen.dart';
import 'app_shell.dart';
import 'auth_state.dart';

const _splashPath = '/splash';
const _loginPath = '/login';
const _registerPath = '/register';
const _playPath = '/play';

GoRouter buildAppRouter(RouterAuthNotifier authNotifier) {
  return GoRouter(
    initialLocation: _splashPath,
    refreshListenable: authNotifier,
    redirect: (context, state) {
      final location = state.matchedLocation;
      final isAuthRoute = location == _loginPath || location == _registerPath;

      if (authNotifier.isResolving) {
        return location == _splashPath ? null : _splashPath;
      }
      if (!authNotifier.isAuthenticated) {
        return isAuthRoute ? null : _loginPath;
      }
      if (isAuthRoute || location == _splashPath) {
        return _playPath;
      }
      return null;
    },
    routes: [
      GoRoute(
        path: _splashPath,
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: _loginPath,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: _registerPath,
        builder: (context, state) => const RegisterScreen(),
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
                routes: [
                  GoRoute(
                    path: 'map',
                    builder: (context, state) => const CourseMapScreen(),
                  ),
                  GoRoute(
                    path: 'new',
                    builder: (context, state) => const CourseCreationScreen(),
                  ),
                  GoRoute(
                    path: ':id',
                    builder: (context, state) => CourseDetailScreen(
                      courseId: state.pathParameters['id']!,
                    ),
                  ),
                ],
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
