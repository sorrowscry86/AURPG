import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

enum ServerStatus { connecting, starting, ready, failed }

class ServerState {
  final ServerStatus status;
  final String baseUrl;
  final String? errorMessage;

  const ServerState({
    required this.status,
    required this.baseUrl,
    this.errorMessage,
  });

  ServerState copyWith({ServerStatus? status, String? baseUrl, String? errorMessage}) =>
      ServerState(
        status: status ?? this.status,
        baseUrl: baseUrl ?? this.baseUrl,
        errorMessage: errorMessage,
      );
}

class ServerNotifier extends AsyncNotifier<ServerState> {
  Process? _process;

  // Reuse a single Dio instance for health pings; closed in onDispose.
  late final Dio _pingDio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 1),
    receiveTimeout: const Duration(seconds: 2),
  ));

  static const _defaultPort = 8000;
  static const _pollInterval = Duration(milliseconds: 500);
  static const _maxAttempts = 20; // 10 seconds

  @override
  Future<ServerState> build() async {
    ref.onDispose(() {
      _process?.kill();
      _pingDio.close();
    });
    // Return the initial state immediately; fire connection logic after build.
    Future(_connect);
    return const ServerState(
      status: ServerStatus.connecting,
      baseUrl: 'http://127.0.0.1:$_defaultPort',
    );
  }

  Future<void> _connect() async {
    const baseUrl = 'http://127.0.0.1:$_defaultPort';

    if (await _ping(baseUrl)) {
      state = AsyncData(ServerState(status: ServerStatus.ready, baseUrl: baseUrl));
      return;
    }

    state = AsyncData(ServerState(status: ServerStatus.starting, baseUrl: baseUrl));
    await _spawnServer();

    for (var i = 0; i < _maxAttempts; i++) {
      await Future<void>.delayed(_pollInterval);
      if (await _ping(baseUrl)) {
        state = AsyncData(ServerState(status: ServerStatus.ready, baseUrl: baseUrl));
        return;
      }
    }

    state = AsyncData(ServerState(
      status: ServerStatus.failed,
      baseUrl: baseUrl,
      errorMessage: 'Engine did not respond within 10 seconds.',
    ));
  }

  Future<bool> _ping(String baseUrl) async {
    try {
      final resp = await _pingDio.get<dynamic>('$baseUrl/health');
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<void> _spawnServer() async {
    // Kill any existing process to prevent port conflicts on retry.
    _process?.kill();
    _process = null;

    final candidates = <List<String>>[
      ['aurpg-server'],
      ['python3', '-m', 'aurpg.server'],
      ['python', '-m', 'aurpg.server'], // Windows fallback
    ];
    for (final cmd in candidates) {
      try {
        _process = await Process.start(
          cmd[0],
          cmd.sublist(1),
          mode: ProcessStartMode.normal,
        );
        // Drain stdout/stderr to prevent OS buffer fill and process hang.
        _process!.stdout.listen((_) {});
        _process!.stderr.listen((_) {});
        return;
      } on ProcessException {
        continue;
      }
    }
  }

  Future<void> retry() async {
    state = const AsyncLoading();
    await _connect();
  }
}

final serverProvider = AsyncNotifierProvider<ServerNotifier, ServerState>(
  ServerNotifier.new,
);

/// Resolves to the base URL only when the server is ready; null otherwise.
final serverBaseUrlProvider = Provider<String?>((ref) {
  final s = ref.watch(serverProvider).valueOrNull;
  return (s?.status == ServerStatus.ready) ? s?.baseUrl : null;
});
