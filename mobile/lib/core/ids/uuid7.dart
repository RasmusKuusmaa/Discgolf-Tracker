import 'package:uuid/uuid.dart';

const Uuid _uuid = Uuid();

/// Generates a UUIDv7 for every locally created entity — its embedded
/// timestamp keeps client-generated IDs roughly sortable and collision-free
/// across devices without a server round trip.
String generateId() => _uuid.v7();
