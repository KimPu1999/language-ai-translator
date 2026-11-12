import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/local_storage/local_library.dart';
import '../../core/localization/app_strings.dart';
import '../../core/providers/app_providers.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings(Localizations.localeOf(context));
    final themeMode = ref.watch(themeModeProvider);
    final locale = ref.watch(localeProvider);
    final library = ref.watch(localLibraryProvider);
    final auth = ref.watch(authProvider);
    return Scaffold(appBar: AppBar(title: Text(strings.settings)), body: ListView(padding: const EdgeInsets.all(16), children: [
      Card(child: ListTile(leading: const Icon(Icons.account_circle_outlined), title: Text(auth.isAuthenticated ? strings.currentUser : strings.signIn, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text(auth.user?.email ?? strings.signInBody), trailing: const Icon(Icons.chevron_right_rounded), onTap: () => context.go(auth.isAuthenticated ? '/account' : '/auth/sign-in'))),
      const SizedBox(height: 12),
      Card(child: SwitchListTile(title: Text(strings.appearance, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text(strings.darkMode), value: themeMode == ThemeMode.dark, onChanged: (value) => ref.read(themeModeProvider.notifier).state = value ? ThemeMode.dark : ThemeMode.light)),
      const SizedBox(height: 12),
      Card(child: ListTile(title: Text(strings.interfaceLanguage, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text(locale.languageCode == 'my' ? 'မြန်မာ' : 'English'), trailing: DropdownButton<String>(value: locale.languageCode, underline: const SizedBox.shrink(), items: const [DropdownMenuItem(value: 'en', child: Text('EN')), DropdownMenuItem(value: 'my', child: Text('MM'))], onChanged: (value) { if (value != null) ref.read(localeProvider.notifier).state = Locale(value); }))),
      const SizedBox(height: 12),
      Card(child: SwitchListTile(title: Text(strings.localSaving, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text(strings.localSavingBody), value: library.enabled, onChanged: (value) => ref.read(localLibraryProvider.notifier).setEnabled(value))),
      const SizedBox(height: 12),
      Card(child: Column(children: [ListTile(leading: const Icon(Icons.history_rounded), title: Text(strings.history), subtitle: Text(auth.isAuthenticated ? strings.historyBody : '${library.history.length} ${strings.localSaving}'), onTap: () => context.go(auth.isAuthenticated ? '/history' : '/auth/sign-in')), ListTile(leading: const Icon(Icons.favorite_border_rounded), title: Text(strings.favorites), subtitle: Text(auth.isAuthenticated ? strings.favoritesBody : '${library.favorites.length} ${strings.localSaving}'), onTap: () => context.go(auth.isAuthenticated ? '/favorites' : '/auth/sign-in'))])),
      if (auth.isAuthenticated) Card(child: ListTile(leading: const Icon(Icons.sync_rounded), title: Text(strings.cloudSync, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text(strings.cloudSyncBody), onTap: () => context.go('/sync'))),
      if (auth.isAuthenticated) ...[const SizedBox(height: 12), Card(child: ListTile(leading: Icon(Icons.logout_rounded, color: Theme.of(context).colorScheme.error), title: Text(strings.signOut, style: TextStyle(color: Theme.of(context).colorScheme.error, fontWeight: FontWeight.w700)), subtitle: Text(strings.signOutBody), onTap: () async { await ref.read(authProvider.notifier).logout(); if (context.mounted) context.go('/auth/sign-in'); }))],
    ]));
  }
}
