import 'package:dio/dio.dart';
import '../models.dart';

class SessionsApi {
  final Dio _dio;
  const SessionsApi(this._dio);

  Future<List<SessionSummary>> listSessions() async {
    final resp = await _dio.get<List<dynamic>>('/sessions');
    return resp.data!
        .map((e) => SessionSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<SessionCreateResponse> createSession(WizardConfigBody body) async {
    final resp = await _dio.post<Map<String, dynamic>>(
      '/sessions',
      data: body.toJson(),
    );
    return SessionCreateResponse.fromJson(resp.data!);
  }

  Future<SessionStateResponse> getState(String sessionId) async {
    final resp = await _dio.get<Map<String, dynamic>>(
      '/sessions/$sessionId/state',
    );
    return SessionStateResponse.fromJson(resp.data!);
  }

  Future<void> deleteSession(String sessionId) async {
    await _dio.delete<void>('/sessions/$sessionId');
  }
}
