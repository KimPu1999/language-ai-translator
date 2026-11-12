import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/auth.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';
import '../../core/theme/app_theme.dart';

class AccountPage extends ConsumerWidget {
  const AccountPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings(Localizations.localeOf(context));
    final user = ref.watch(authProvider).user!;
    return Scaffold(appBar: AppBar(title: Text(strings.accountSettings)), body: ListView(padding: const EdgeInsets.all(16), children: [
      Card(child: ListTile(leading: const CircleAvatar(child: Icon(Icons.person_outline_rounded)), title: Text(user.email, style: const TextStyle(fontWeight: FontWeight.w800)), subtitle: Text(user.emailVerified ? strings.verified : strings.unverified))),
      const SizedBox(height: 12),
      _AccountLink(icon: Icons.person_outline_rounded, title: strings.profile, onTap: () => context.go('/profile')),
      _AccountLink(icon: Icons.devices_other_rounded, title: strings.sessions, onTap: () => context.go('/security')),
      _AccountLink(icon: Icons.history_rounded, title: strings.history, onTap: () => context.go('/history')),
      _AccountLink(icon: Icons.favorite_border_rounded, title: strings.favorites, onTap: () => context.go('/favorites')),
      _AccountLink(icon: Icons.sync_rounded, title: strings.cloudSync, onTap: () => context.go('/sync')),
      const SizedBox(height: 18),
      Card(child: ListTile(leading: Icon(Icons.logout_rounded, color: Theme.of(context).colorScheme.error), title: Text(strings.signOut, style: TextStyle(color: Theme.of(context).colorScheme.error, fontWeight: FontWeight.w800)), subtitle: Text(strings.signOutBody), onTap: () => _logout(context, ref))),
    ]));
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    await ref.read(authProvider.notifier).logout();
    if (context.mounted) context.go('/auth/sign-in');
  }
}

class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});
  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage> {
  late Future<UserProfile> _future;
  final _displayName = TextEditingController();
  bool _saving = false;
  String? _error;
  @override
  void initState() { super.initState(); _future = ref.read(apiClientProvider).getProfile(); }
  @override
  void dispose() { _displayName.dispose(); super.dispose(); }
  Future<void> _save() async { setState(() { _saving = true; _error = null; }); try { await ref.read(apiClientProvider).updateProfile(displayName: _displayName.text.trim().isEmpty ? null : _displayName.text.trim()); if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppStrings(Localizations.localeOf(context)).saved))); } on ApiFailure catch (error) { if (mounted) setState(() => _error = error.message); } finally { if (mounted) setState(() => _saving = false); } }
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); return Scaffold(appBar: AppBar(title: Text(strings.profile)), body: FutureBuilder<UserProfile>(future: _future, builder: (context, snapshot) { if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator()); if (snapshot.hasError) return _ErrorState(error: snapshot.error.toString(), onRetry: () => setState(() => _future = ref.read(apiClientProvider).getProfile())); final profile = snapshot.data!; if (_displayName.text.isEmpty) _displayName.text = profile.displayName ?? ''; return ListView(padding: const EdgeInsets.all(16), children: [Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(strings.accountSettings, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)), const SizedBox(height: 18), TextFormField(initialValue: profile.email, readOnly: true, decoration: InputDecoration(labelText: strings.email)), const SizedBox(height: 14), TextField(controller: _displayName, maxLength: 100, decoration: InputDecoration(labelText: strings.displayName)), const SizedBox(height: 8), FilledButton.icon(onPressed: _saving ? null : _save, icon: _saving ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.save_outlined), label: Text(strings.saveChanges)), if (_error != null) ...[const SizedBox(height: 12), Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))]]))), const SizedBox(height: 12), ListTile(leading: Icon(profile.emailVerified ? Icons.verified_outlined : Icons.warning_amber_outlined, color: profile.emailVerified ? AppTheme.blue : Colors.orange), title: Text(profile.emailVerified ? strings.verified : strings.unverified), subtitle: Text(profile.createdAt.toLocal().toString().split(' ').first))]); }); }
}

class SecurityPage extends ConsumerStatefulWidget {
  const SecurityPage({super.key});
  @override
  ConsumerState<SecurityPage> createState() => _SecurityPageState();
}

class _SecurityPageState extends ConsumerState<SecurityPage> {
  late Future<List<AuthSession>> _future;
  @override
  void initState() { super.initState(); _future = ref.read(apiClientProvider).getSessions(); }
  Future<void> _revoke(String id) async { try { await ref.read(apiClientProvider).revokeSession(id); if (mounted) setState(() => _future = ref.read(apiClientProvider).getSessions()); } on ApiFailure catch (error) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message))); } }
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); return Scaffold(appBar: AppBar(title: Text(strings.sessions)), body: FutureBuilder<List<AuthSession>>(future: _future, builder: (context, snapshot) { if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator()); if (snapshot.hasError) return _ErrorState(error: snapshot.error.toString(), onRetry: () => setState(() => _future = ref.read(apiClientProvider).getSessions())); final sessions = snapshot.data ?? const <AuthSession>[]; if (sessions.isEmpty) return Center(child: Text(strings.noSessions)); return ListView.separated(padding: const EdgeInsets.all(16), itemCount: sessions.length, separatorBuilder: (_, __) => const SizedBox(height: 10), itemBuilder: (context, index) { final session = sessions[index]; return Card(child: ListTile(leading: const Icon(Icons.laptop_mac_outlined), title: Text(session.deviceName ?? strings.sessions, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text('${session.current ? strings.currentSession : session.userAgent ?? ''}\n${strings.lastActive}: ${session.lastSeenAt.toLocal()}\n${strings.expires}: ${session.expiresAt.toLocal()}'), isThreeLine: true, trailing: session.current ? Chip(label: Text(strings.currentSession)) : TextButton(onPressed: () => _revoke(session.id), child: Text(strings.revoke)))); }]); }); }
}

class _AccountLink extends StatelessWidget {
  const _AccountLink({required this.icon, required this.title, required this.onTap});
  final IconData icon;
  final String title;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Card(child: ListTile(leading: Icon(icon, color: AppTheme.blue), title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)), trailing: const Icon(Icons.chevron_right_rounded), onTap: onTap));
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});
  final String error;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Text(error, textAlign: TextAlign.center), const SizedBox(height: 12), OutlinedButton(onPressed: onRetry, child: Text(AppStrings(Localizations.localeOf(context)).retry))])));
}
