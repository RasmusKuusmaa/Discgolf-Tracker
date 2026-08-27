import 'package:connectivity_plus/connectivity_plus.dart';

/// Exposes the device's online/offline status as a stream. Reflects
/// whether the OS reports an active network interface, not confirmed
/// reachability of our own backend.
class ConnectivityService {
  ConnectivityService([Connectivity? connectivity]) : _connectivity = connectivity ?? Connectivity();

  final Connectivity _connectivity;

  Stream<bool> get onlineStatus => _connectivity.onConnectivityChanged.map(_isOnline);

  Future<bool> get isOnline async => _isOnline(await _connectivity.checkConnectivity());

  bool _isOnline(List<ConnectivityResult> results) =>
      results.any((result) => result != ConnectivityResult.none);
}
