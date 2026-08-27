import 'dart:convert';

/// A syntactically valid (unsigned) JWT for tests — `AuthApi` only reads the
/// `exp` claim out of the payload segment, it never verifies the signature.
String fakeJwt({required int exp}) {
  final String payload = base64Url.encode(utf8.encode(jsonEncode({'exp': exp})));
  return 'header.$payload.signature';
}
