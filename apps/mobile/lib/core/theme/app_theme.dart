import 'package:flutter/material.dart';

class AppTheme {
  static const navy = Color(0xFF102A56);
  static const blue = Color(0xFF2563EB);
  static const mist = Color(0xFFF5F8FC);
  static const ink = Color(0xFF11233F);

  static ThemeData light() => _theme(Brightness.light);
  static ThemeData dark() => _theme(Brightness.dark);

  static ThemeData _theme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final scheme = ColorScheme.fromSeed(seedColor: blue, brightness: brightness).copyWith(primary: blue, surface: isDark ? const Color(0xFF13233B) : Colors.white);
    return ThemeData(
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: isDark ? const Color(0xFF0D1728) : mist,
      fontFamily: 'Inter',
      fontFamilyFallback: const ['Noto Sans Myanmar', 'Arial'],
      useMaterial3: true,
      textTheme: (isDark ? Typography.material2021(platform: TargetPlatform.iOS, colorScheme: scheme).white : Typography.material2021(platform: TargetPlatform.iOS, colorScheme: scheme).black).apply(fontFamily: 'Inter', fontFamilyFallback: const ['Noto Sans Myanmar', 'Arial']),
      appBarTheme: AppBarTheme(backgroundColor: isDark ? const Color(0xFF101D31) : Colors.white, foregroundColor: isDark ? Colors.white : ink, elevation: 0, centerTitle: false),
      navigationBarTheme: NavigationBarThemeData(backgroundColor: isDark ? const Color(0xFF101D31) : Colors.white, indicatorColor: isDark ? const Color(0xFF214779) : const Color(0xFFE9F2FF), labelTextStyle: MaterialStatePropertyAll(TextStyle(fontWeight: FontWeight.w700, fontSize: 11, fontFamilyFallback: const ['Noto Sans Myanmar']))),
      inputDecorationTheme: InputDecorationTheme(filled: true, fillColor: isDark ? const Color(0xFF13233B) : Colors.white, border: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide(color: isDark ? const Color(0xFF29415F) : const Color(0xFFE2E8F0))), enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide(color: isDark ? const Color(0xFF29415F) : const Color(0xFFE2E8F0))), focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: const BorderSide(color: blue, width: 2))),
    );
  }
}

