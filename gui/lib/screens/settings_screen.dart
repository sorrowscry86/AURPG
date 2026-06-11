import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart';
import '../providers/settings_provider.dart';
import '../theme/app_theme.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final _apiKeyCtrl = TextEditingController();
  final _savesDirCtrl = TextEditingController();
  final _portCtrl = TextEditingController();

  bool _obscureKey = true;
  bool _dirty = false;
  bool _hydrated = false;

  String? _provider;
  String? _model;
  List<ModelInfo> _models = [];
  bool _loadingModels = false;

  @override
  void dispose() {
    _apiKeyCtrl.dispose();
    _savesDirCtrl.dispose();
    _portCtrl.dispose();
    super.dispose();
  }

  void _hydrate(AppSettings s) {
    if (_hydrated) return;
    _hydrated = true;
    _provider = s.provider;
    _model = s.model;
    _savesDirCtrl.text = s.savesDir;
    _portCtrl.text = s.port.toString();
  }

  void _markDirty() => setState(() => _dirty = true);

  Future<void> _loadModels() async {
    setState(() => _loadingModels = true);
    try {
      final resp = await ref.read(settingsProvider.notifier).fetchModels();
      setState(() {
        _models = resp.models;
        if (!_models.any((m) => m.id == _model) && _models.isNotEmpty) {
          _model = _models.first.id;
        }
      });
    } catch (e) {
      _showSnack('Failed to fetch models: $e');
    } finally {
      setState(() => _loadingModels = false);
    }
  }

  Future<void> _save() async {
    final key = _apiKeyCtrl.text.trim();
    final port = int.tryParse(_portCtrl.text.trim());
    final saves = _savesDirCtrl.text.trim();
    try {
      await ref.read(settingsProvider.notifier).save(
            provider: _provider,
            apiKey: key.isNotEmpty ? key : null,
            model: _model,
            savesDir: saves.isNotEmpty ? saves : null,
            port: port,
          );
      setState(() {
        _dirty = false;
        _apiKeyCtrl.clear();
      });
      _showSnack('Settings saved.');
    } catch (e) {
      _showSnack('Save failed: $e');
    }
  }

  void _showSnack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    final settingsAsync = ref.watch(settingsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: TextButton.icon(
              onPressed: _dirty ? _save : null,
              icon: const Icon(Icons.save_outlined),
              label: const Text('Save'),
            ),
          ),
        ],
      ),
      body: settingsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (settings) {
          _hydrate(settings);
          return _buildForm(settings);
        },
      ),
    );
  }

  Widget _buildForm(AppSettings settings) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 540),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Section('LLM Provider'),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _provider,
              decoration: const InputDecoration(labelText: 'Provider'),
              items: const [
                DropdownMenuItem(value: 'anthropic', child: Text('Anthropic')),
                DropdownMenuItem(value: 'openrouter', child: Text('OpenRouter')),
              ],
              onChanged: (v) => setState(() {
                _provider = v;
                _models = [];
                _model = null;
                _dirty = true;
              }),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _apiKeyCtrl,
              obscureText: _obscureKey,
              decoration: InputDecoration(
                labelText: 'API Key',
                hintText: settings.apiKeySet
                    ? 'Set (${settings.apiKeyPreview}) — enter to replace'
                    : 'Paste key here',
                suffixIcon: IconButton(
                  icon: Icon(_obscureKey ? Icons.visibility_off : Icons.visibility),
                  onPressed: () => setState(() => _obscureKey = !_obscureKey),
                ),
              ),
              onChanged: (_) => _markDirty(),
            ),
            const SizedBox(height: 28),
            _Section('Model'),
            const SizedBox(height: 12),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: _models.isEmpty
                      ? TextFormField(
                          key: const ValueKey('model_text'),
                          initialValue: settings.model,
                          decoration: const InputDecoration(
                            labelText: 'Model ID',
                            hintText: 'e.g. claude-haiku-4-5-20251001',
                          ),
                          onChanged: (v) => setState(() {
                            _model = v;
                            _dirty = true;
                          }),
                        )
                      : DropdownButtonFormField<String>(
                          key: const ValueKey('model_dropdown'),
                          value: _model,
                          decoration: const InputDecoration(labelText: 'Model'),
                          items: _models
                              .map((m) => DropdownMenuItem(
                                    value: m.id,
                                    child: Text(
                                      m.name.isNotEmpty ? m.name : m.id,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ))
                              .toList(),
                          onChanged: (v) => setState(() {
                            _model = v;
                            _dirty = true;
                          }),
                        ),
                ),
                const SizedBox(width: 10),
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: IconButton.outlined(
                    tooltip: 'Fetch available models',
                    onPressed: _loadingModels ? null : _loadModels,
                    icon: _loadingModels
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.refresh),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 28),
            _Section('Storage & Server'),
            const SizedBox(height: 12),
            TextFormField(
              controller: _savesDirCtrl,
              decoration: const InputDecoration(
                labelText: 'Saves Directory',
                hintText: '~/.aurpg/saves',
              ),
              onChanged: (_) => _markDirty(),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _portCtrl,
              decoration: const InputDecoration(
                labelText: 'Server Port',
                hintText: '8000',
              ),
              keyboardType: TextInputType.number,
              onChanged: (_) => _markDirty(),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _dirty ? _save : null,
                icon: const Icon(Icons.save),
                label: const Text('Save Settings'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String label;
  const _Section(this.label);

  @override
  Widget build(BuildContext context) {
    return Text(
      label.toUpperCase(),
      style: const TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: AppTheme.ledgerAccent,
        letterSpacing: 1.4,
      ),
    );
  }
}
