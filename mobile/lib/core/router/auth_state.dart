import 'package:flutter/foundation.dart';

/// Minimal auth signal for router redirects.
///
/// Replaced by the real session state in Phase 10 (`AuthController`), which
/// will update [isAuthenticated] as the session is restored, logged in, or
/// logged out.
class AuthState extends ChangeNotifier {
  bool _isAuthenticated = false;

  bool get isAuthenticated => _isAuthenticated;

  void setAuthenticated(bool value) {
    if (_isAuthenticated == value) return;
    _isAuthenticated = value;
    notifyListeners();
  }
}
