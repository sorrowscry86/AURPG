import 'package:dio/dio.dart';

class AurpgException implements Exception {
  final int statusCode;
  final String message;
  const AurpgException(this.statusCode, this.message);

  @override
  String toString() => 'AurpgException($statusCode): $message';
}

Dio createDioClient(String baseUrl) {
  final dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    connectTimeout: const Duration(seconds: 5),
    receiveTimeout: const Duration(minutes: 5), // LLM calls can be slow
    sendTimeout: const Duration(seconds: 10),
    headers: const {'Content-Type': 'application/json'},
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onError: (e, handler) {
      if (e.response != null) {
        final status = e.response!.statusCode ?? 0;
        final data = e.response!.data;
        final detail = data is Map ? (data['detail'] ?? e.message ?? 'Unknown') : (e.message ?? 'Unknown');
        return handler.reject(DioException(
          requestOptions: e.requestOptions,
          error: AurpgException(status, detail.toString()),
          response: e.response,
          type: DioExceptionType.badResponse,
        ));
      }
      handler.next(e);
    },
  ));

  return dio;
}
