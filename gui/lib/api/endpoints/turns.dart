import 'package:dio/dio.dart';
import '../models.dart';

class TurnsApi {
  final Dio _dio;
  const TurnsApi(this._dio);

  Future<TurnResponse> postTurn(String sessionId, String playerInput) async {
    final resp = await _dio.post<Map<String, dynamic>>(
      '/sessions/$sessionId/turn',
      data: {'player_input': playerInput},
    );
    return TurnResponse.fromJson(resp.data!);
  }
}
