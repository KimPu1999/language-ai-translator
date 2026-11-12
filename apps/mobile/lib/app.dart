import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/localization/app_strings.dart';
import 'core/providers/app_providers.dart';
import 'core/theme/app_theme.dart';
import 'features/camera/camera_page.dart';
import 'features/documents/documents_page.dart';
import 'features/favorites/favorites_page.dart';
import 'features/history/history_page.dart';
import 'features/home/home_page.dart';
import 'features/settings/settings_page.dart';
import 'features/text/text_page.dart';
import 'features/voice/voice_page.dart';
import 'features/conversation/conversation_page.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();

class LinguaApp extends ConsumerWidget {
  const LinguaApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) { final locale = ref.watch(localeProvider); final themeMode = ref.watch(themeModeProvider); return MaterialApp.router(title: 'Lingua', theme: AppTheme.light(), darkTheme: AppTheme.dark(), themeMode: themeMode, locale: locale, supportedLocales: const [Locale('en'), Locale('my')], localizationsDelegates: const [AppStringsDelegate(), GlobalMaterialLocalizations.delegate, GlobalWidgetsLocalizations.delegate, GlobalCupertinoLocalizations.delegate], routerConfig: _router); }
}

final _router = GoRouter(navigatorKey: _rootNavigatorKey, initialLocation: '/text', routes: [GoRoute(path: '/', redirect: (_, __) => '/home'), ShellRoute(builder: (context, state, child) => _AppShell(child: child, location: state.uri.path), routes: [GoRoute(path: '/home', pageBuilder: (context, state) => const NoTransitionPage(child: HomePage())), GoRoute(path: '/text', pageBuilder: (context, state) => const NoTransitionPage(child: TextPage())), GoRoute(path: '/voice', pageBuilder: (context, state) => const NoTransitionPage(child: VoicePage())), GoRoute(path: '/conversation', pageBuilder: (context, state) => const NoTransitionPage(child: ConversationPage())), GoRoute(path: '/camera', pageBuilder: (context, state) => const NoTransitionPage(child: CameraPage())), GoRoute(path: '/documents', pageBuilder: (context, state) => const NoTransitionPage(child: DocumentsPage())), GoRoute(path: '/history', pageBuilder: (context, state) => const NoTransitionPage(child: HistoryPage())), GoRoute(path: '/favorites', pageBuilder: (context, state) => const NoTransitionPage(child: FavoritesPage())), GoRoute(path: '/settings', pageBuilder: (context, state) => const NoTransitionPage(child: SettingsPage()))])]);

class _AppShell extends StatelessWidget {
  const _AppShell({required this.child, required this.location});
  final Widget child;
  final String location;
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); final index = switch (location) { '/text' => 0, '/voice' => 1, '/camera' => 2, '/documents' => 3, _ => 4 }; return Scaffold(body: child, bottomNavigationBar: NavigationBar(selectedIndex: index, onDestinationSelected: (next) { final route = switch (next) { 0 => '/text', 1 => '/voice', 2 => '/camera', 3 => '/documents', _ => '/settings' }; context.go(route); }, destinations: [NavigationDestination(icon: const Icon(Icons.translate_rounded), label: strings.text), NavigationDestination(icon: const Icon(Icons.mic_none_rounded), label: strings.voice), NavigationDestination(icon: const Icon(Icons.camera_alt_outlined), label: strings.camera), NavigationDestination(icon: const Icon(Icons.description_outlined), label: strings.documents), NavigationDestination(icon: const Icon(Icons.more_horiz_rounded), label: strings.more)])); }
}

