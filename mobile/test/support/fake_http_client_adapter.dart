import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

typedef FakeResponder = ResponseBody Function(RequestOptions options);

/// Minimal [HttpClientAdapter] for tests: maps `METHOD path` to a canned
/// [ResponseBody] so requests never leave the process. Register a fresh
/// responder per key; a responder closure can hold its own counter to vary
/// behaviour across repeated calls to the same endpoint.
class FakeHttpClientAdapter implements HttpClientAdapter {
  FakeHttpClientAdapter(this._responders);

  final Map<String, FakeResponder> _responders;
  final List<RequestOptions> requests = [];

  int countOf(String method, String path) =>
      requests.where((r) => r.method == method && r.path == path).length;

  static ResponseBody json(Object body, int statusCode) {
    return ResponseBody.fromString(
      jsonEncode(body),
      statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    final String key = '${options.method} ${options.path}';
    final FakeResponder? responder = _responders[key];
    if (responder == null) {
      throw StateError('No fake response registered for $key');
    }
    return responder(options);
  }

  @override
  void close({bool force = false}) {}
}
