import 'package:dio/dio.dart';
import '../models.dart';

class HealthApi {
  final Dio _dio;
  const HealthApi(this._dio);

  Future<HealthResponse> getHealth() async {
    final resp = await _dio.get<Map<String, dynamic>>('/health');
    final data = resp.data;
    if (data == null) throw const FormatException('Health response data was null');
    return HealthResponse.fromJson(data);
  }
}
