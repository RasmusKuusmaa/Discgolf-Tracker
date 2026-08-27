import '../../domain/models/auth_tokens.dart';

/// Persists the current session's tokens across app restarts.
abstract class TokenStore {
  Future<AuthTokens?> readTokens();
  Future<void> saveTokens(AuthTokens tokens);
  Future<void> clearTokens();
}
