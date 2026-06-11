import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/server_provider.dart';
import '../theme/app_theme.dart';

class StartupScreen extends ConsumerWidget {
  const StartupScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final serverAsync = ref.watch(serverProvider);

    return serverAsync.when(
      loading: () => _Loading('Connecting to engine…'),
      error: (e, _) => _Error(ref, e.toString()),
      data: (server) {
        switch (server.status) {
          case ServerStatus.connecting:
            return _Loading('Connecting to engine…');
          case ServerStatus.starting:
            return _Loading('Starting engine…');
          case ServerStatus.ready:
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (context.mounted) context.go('/home');
            });
            return _Loading('Engine ready…');
          case ServerStatus.failed:
            return _Error(ref, server.errorMessage ?? 'Unknown error');
        }
      },
    );
  }
}

class _Loading extends StatelessWidget {
  final String message;
  const _Loading(this.message);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.canvasColor,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 48,
              height: 48,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(height: 20),
            Text(message, style: const TextStyle(color: AppTheme.onSurfaceColor)),
          ],
        ),
      ),
    );
  }
}

class _Error extends ConsumerWidget {
  final String message;
  const _Error(WidgetRef _, this.message);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppTheme.canvasColor,
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.error_outline, color: AppTheme.dangerColor, size: 48),
                  const SizedBox(height: 16),
                  const Text(
                    'Engine failed to start',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    message,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppTheme.onSurfaceColor),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'pip install -e ".[server]"\naurpg-server',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                      color: AppTheme.ledgerAccent,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: () => ref.read(serverProvider.notifier).retry(),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
