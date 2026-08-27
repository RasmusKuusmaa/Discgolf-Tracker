import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/models/auth_state.dart' as domain;
import '../../features/auth/providers/auth_controller.dart';

/// Bridges [AuthController]'s Riverpod state to `go_router`'s
/// `Listenable`-based `refreshListenable`, so redirects re-evaluate
/// whenever the session changes (restored, logged in, logged out).
class RouterAuthNotifier extends ChangeNotifier {
  RouterAuthNotifier(this._ref) {
    _subscription = _ref.listen<domain.AuthState>(
      authControllerProvider,
      (previous, next) => notifyListeners(),
    );
  }

  final Ref _ref;
  late final ProviderSubscription<domain.AuthState> _subscription;

  domain.AuthState get _state => _ref.read(authControllerProvider);

  /// True while the session is still being restored on launch — the
  /// router shows a splash screen instead of routing to login or home.
  bool get isResolving =>
      _state is domain.AuthInitial || _state is domain.AuthAuthenticating;

  bool get isAuthenticated => _state is domain.AuthAuthenticated;

  @override
  void dispose() {
    _subscription.close();
    super.dispose();
  }
}

final Provider<RouterAuthNotifier> routerAuthNotifierProvider =
    Provider<RouterAuthNotifier>((ref) {
      final RouterAuthNotifier notifier = RouterAuthNotifier(ref);
      ref.onDispose(notifier.dispose);
      return notifier;
    });
