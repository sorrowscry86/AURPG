import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const _canvas = Color(0xFF0F0F14);
  static const _surface = Color(0xFF1A1A24);
  static const _surfaceHigh = Color(0xFF24243A);
  static const _onSurface = Color(0xFFE8E8F0);
  static const _accent = Color(0xFF9B7FE8);
  static const _danger = Color(0xFFE87F7F);
  static const _success = Color(0xFF7FE8A0);
  static const _warning = Color(0xFFE8C87F);

  static ThemeData get dark {
    final base = ThemeData.dark(useMaterial3: true);
    return base.copyWith(
      colorScheme: ColorScheme.dark(
        primary: _accent,
        secondary: _success,
        error: _danger,
        surface: _surface,
        onSurface: _onSurface,
        surfaceContainerHighest: _surfaceHigh,
        outline: _accent.withValues(alpha: 0.3),
      ),
      scaffoldBackgroundColor: _canvas,
      textTheme: GoogleFonts.interTextTheme(base.textTheme).apply(
        bodyColor: _onSurface,
        displayColor: _onSurface,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: _surface,
        foregroundColor: _onSurface,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        color: _surface,
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: _surfaceHigh,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: _accent.withValues(alpha: 0.3)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: _accent.withValues(alpha: 0.2)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: _accent),
        ),
        labelStyle: const TextStyle(color: _onSurface),
        hintStyle: TextStyle(color: _onSurface.withValues(alpha: 0.4)),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: _accent,
          foregroundColor: _canvas,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: _surfaceHigh,
        labelStyle: const TextStyle(color: _onSurface, fontSize: 12),
        side: BorderSide(color: _accent.withValues(alpha: 0.3)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      ),
      dividerTheme: DividerThemeData(color: _accent.withValues(alpha: 0.15)),
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: _surface,
        contentTextStyle: TextStyle(color: _onSurface),
      ),
    );
  }

  static const ledgerAccent = _accent;
  static const dangerColor = _danger;
  static const successColor = _success;
  static const warningColor = _warning;
  static const canvasColor = _canvas;
  static const surfaceColor = _surface;
  static const onSurfaceColor = _onSurface;
}
