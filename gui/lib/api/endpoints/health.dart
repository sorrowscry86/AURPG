import 'package:dio/dio.dart';
import '../models.dart';

class HealthApi {
  final Dio _dio;
  const HealthApi(this._dio);

  Future<HealthResponse> getHealth() async {
    final resp = await _dio.get<Map<String, dynamic>>('/health');
    return HealthResponse.fromJson(resp.data!);
  }
}
