import 'package:discgolf_tracker/data/local/token_store.dart';
import 'package:discgolf_tracker/domain/models/auth_tokens.dart';

/// In-memory [TokenStore] for tests — no platform channel involved.
class InMemoryTokenStore implements TokenStore {
  InMemoryTokenStore([this._tokens]);

  AuthTokens? _tokens;

  @override
  Future<AuthTokens?> readTokens() async => _tokens;

  @override
  Future<void> saveTokens(AuthTokens tokens) async {
    _tokens = tokens;
  }

  @override
  Future<void> clearTokens() async {
    _tokens = null;
  }
}
