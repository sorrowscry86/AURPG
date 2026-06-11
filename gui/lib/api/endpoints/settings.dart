import 'package:dio/dio.dart';
import '../models.dart';

class SettingsApi {
  final Dio _dio;
  const SettingsApi(this._dio);

  Future<AppSettings> getSettings() async {
    final resp = await _dio.get<Map<String, dynamic>>('/settings');
    return AppSettings.fromJson(resp.data!);
  }

  Future<AppSettings> updateSettings({
    String? provider,
    String? apiKey,
    String? model,
    String? savesDir,
    int? port,
  }) async {
    final body = <String, dynamic>{};
    if (provider != null) body['provider'] = provider;
    if (apiKey != null) body['api_key'] = apiKey;
    if (model != null) body['model'] = model;
    if (savesDir != null) body['saves_dir'] = savesDir;
    if (port != null) body['port'] = port;
    final resp = await _dio.put<Map<String, dynamic>>('/settings', data: body);
    return AppSettings.fromJson(resp.data!);
  }

  Future<ModelsResponse> getModels() async {
    final resp = await _dio.get<Map<String, dynamic>>('/models');
    return ModelsResponse.fromJson(resp.data!);
  }
}
