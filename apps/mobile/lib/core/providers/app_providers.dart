import 'dart:ui';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/language.dart';
import '../network/api_client.dart';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

final languagesProvider = FutureProvider<List<Language>>((ref) async {
  final raw = await ref.watch(apiClientProvider).getLanguages();
  return raw.map(Language.fromJson).toList();
});

final capabilitiesProvider = FutureProvider<Capabilities>((ref) async {
  final raw = await ref.watch(apiClientProvider).getCapabilities();
  return Capabilities.fromJson(raw);
});

final localeProvider = StateProvider<Locale>((ref) => const Locale('en'));
final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.light);

