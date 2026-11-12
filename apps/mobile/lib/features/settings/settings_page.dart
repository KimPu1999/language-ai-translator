import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/localization/app_strings.dart';
import '../../core/providers/app_providers.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) { final strings = AppStrings(Localizations.localeOf(context)); final themeMode = ref.watch(themeModeProvider); final locale = ref.watch(localeProvider); return Scaffold(appBar: AppBar(title: Text(strings.settings)), body: ListView(padding: const EdgeInsets.all(16), children: [Card(child: SwitchListTile(title: Text(strings.appearance, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text(strings.darkMode), value: themeMode == ThemeMode.dark, onChanged: (value) => ref.read(themeModeProvider.notifier).state = value ? ThemeMode.dark : ThemeMode.light)), const SizedBox(height: 12), Card(child: ListTile(title: Text(strings.interfaceLanguage, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text(locale.languageCode == 'my' ? 'မြန်မာ' : 'English'), trailing: DropdownButton<String>(value: locale.languageCode, underline: const SizedBox.shrink(), items: const [DropdownMenuItem(value: 'en', child: Text('EN')), DropdownMenuItem(value: 'my', child: Text('MM'))], onChanged: (value) { if (value != null) ref.read(localeProvider.notifier).state = Locale(value); }))), const SizedBox(height: 12), Card(child: Column(children: [ListTile(leading: const Icon(Icons.history_rounded), title: Text(strings.noHistory), onTap: () => context.go('/history')), ListTile(leading: const Icon(Icons.favorite_border_rounded), title: Text(strings.noFavorites), onTap: () => context.go('/favorites'))]))]); }
}

