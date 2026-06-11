import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Placeholder — filled out fully in Checkpoint 2 (M4).
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AURPG'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: 'Settings',
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.auto_stories, size: 64, color: Colors.white24),
            const SizedBox(height: 16),
            const Text(
              'No saved sessions.',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            const Text(
              'Tap + to start a new campaign.',
              style: TextStyle(color: Colors.white54),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {}, // Wizard — Checkpoint 2
        icon: const Icon(Icons.add),
        label: const Text('New Campaign'),
      ),
    );
  }
}
