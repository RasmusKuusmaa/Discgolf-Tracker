import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../domain/models/auth_tokens.dart';
import 'token_store.dart';

/// [TokenStore] backed by the platform keychain/keystore via
/// `flutter_secure_storage`.
class SecureTokenStore implements TokenStore {
  SecureTokenStore({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  static const String _key = 'auth_tokens';

  final FlutterSecureStorage _storage;

  @override
  Future<AuthTokens?> readTokens() async {
    final String? raw = await _storage.read(key: _key);
    if (raw == null) {
      return null;
    }
    return AuthTokens.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }

  @override
  Future<void> saveTokens(AuthTokens tokens) {
    return _storage.write(key: _key, value: jsonEncode(tokens.toJson()));
  }

  @override
  Future<void> clearTokens() {
    return _storage.delete(key: _key);
  }
}
