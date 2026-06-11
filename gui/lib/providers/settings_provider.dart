import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/client.dart';
import '../api/endpoints/settings.dart';
import '../api/models.dart';
import 'server_provider.dart';

class SettingsNotifier extends AsyncNotifier<AppSettings> {
  SettingsApi _api(String baseUrl) => SettingsApi(createDioClient(baseUrl));

  @override
  Future<AppSettings> build() async {
    final server = await ref.watch(serverProvider.future);
    if (server.status != ServerStatus.ready) {
      throw StateError('Server not ready');
    }
    return _api(server.baseUrl).getSettings();
  }

  Future<void> save({
    String? provider,
    String? apiKey,
    String? model,
    String? savesDir,
    int? port,
  }) async {
    final baseUrl = ref.read(serverBaseUrlProvider);
    if (baseUrl == null) throw StateError('Server not ready');
    final updated = await _api(baseUrl).updateSettings(
      provider: provider,
      apiKey: apiKey,
      model: model,
      savesDir: savesDir,
      port: port,
    );
    state = AsyncData(updated);
  }

  Future<ModelsResponse> fetchModels() async {
    final baseUrl = ref.read(serverBaseUrlProvider);
    if (baseUrl == null) throw StateError('Server not ready');
    return _api(baseUrl).getModels();
  }

  Future<void> refresh() async {
    final baseUrl = ref.read(serverBaseUrlProvider);
    if (baseUrl == null) return;
    state = AsyncData(await _api(baseUrl).getSettings());
  }
}

final settingsProvider = AsyncNotifierProvider<SettingsNotifier, AppSettings>(
  SettingsNotifier.new,
);
