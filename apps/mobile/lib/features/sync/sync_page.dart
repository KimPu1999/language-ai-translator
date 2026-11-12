import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/local_storage/local_library.dart';
import '../../core/localization/app_strings.dart';
import '../../core/models/sync.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';
import '../../core/sync/sync_queue.dart';

class SyncPage extends ConsumerStatefulWidget {
  const SyncPage({super.key});
  @override
  ConsumerState<SyncPage> createState() => _SyncPageState();
}

class _SyncPageState extends ConsumerState<SyncPage> {
  SyncStatus? _status;
  String? _error;
  bool _busy = true;
  final Set<String> _selected = <String>{};

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() { _busy = true; _error = null; });
    try {
      final status = await ref.read(apiClientProvider).getSyncStatus();
      if (!mounted) return;
      setState(() { _status = status; _busy = false; });
      final user = ref.read(authProvider).user;
      if (status.enabled && user != null) await ref.read(syncQueueProvider.notifier).flush(user.id, ref.read(apiClientProvider));
    } on ApiFailure catch (error) { if (mounted) setState(() { _error = error.message; _busy = false; }); }
  }

  List<SyncRecord> _records(LocalLibraryState library) => [
        ...library.history.map((item) => SyncRecord(entityType: 'translation', clientRecordId: item.id, clientUpdatedAt: item.updatedAt ?? item.createdAt, sourceLanguage: item.sourceLanguage, targetLanguage: item.targetLanguage, sourceText: item.sourceText, translatedText: item.translatedText, provider: 'local')),
        ...library.favorites.map((item) => SyncRecord(entityType: 'favorite', clientRecordId: '${item.id}:favorite', clientUpdatedAt: item.updatedAt ?? item.createdAt, translationClientRecordId: item.id)),
      ];

  Future<void> _toggleConsent(bool enabled) async {
    try { setState(() => _busy = true); final status = await ref.read(apiClientProvider).setSyncConsent(enabled); if (mounted) setState(() { _status = status; _busy = false; }); }
    on ApiFailure catch (error) { if (mounted) setState(() { _error = error.message; _busy = false; }); }
  }

  Future<void> _upload(List<SyncRecord> records) async {
    final chosen = records.where((record) => _selected.contains(record.clientRecordId)).toList();
    if (chosen.isEmpty) return;
    try {
      await ref.read(apiClientProvider).previewSync(chosen);
      final locale = ref.read(localeProvider).languageCode;
      final theme = ref.read(themeModeProvider) == ThemeMode.dark ? 'dark' : 'light';
      await ref.read(apiClientProvider).updateSyncPreferences(locale: locale, theme: theme);
      await ref.read(apiClientProvider).importSync(chosen, idempotencyKey: 'mobile-${DateTime.now().microsecondsSinceEpoch}');
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppStrings(Localizations.localeOf(context)).saved)));
    } catch (error) {
      final user = ref.read(authProvider).user;
      if (user != null) await ref.read(syncQueueProvider.notifier).enqueue(user.id, chosen);
      if (mounted) setState(() => _error = error is ApiFailure ? error.message : error.toString());
    }
  }

  Future<void> _download() async {
    try {
      final pages = <SyncChange>[];
      String? cursor;
      do {
        final page = await ref.read(apiClientProvider).getSyncChanges(cursor: cursor);
        pages.addAll(page.items);
        cursor = page.hasMore ? page.nextCursor : null;
        if (page.hasMore && cursor == null) break;
      } while (cursor != null);
      final remote = await ref.read(apiClientProvider).getSyncStatus();
      if (mounted) {
        ref.read(localeProvider.notifier).state = Locale(remote.locale);
        if (remote.theme == 'dark') ref.read(themeModeProvider.notifier).state = ThemeMode.dark;
        if (remote.theme == 'light') ref.read(themeModeProvider.notifier).state = ThemeMode.light;
      }
      final translations = pages.where((item) => item.entityType == 'translation' && !item.deleted && item.sourceText != null && item.translatedText != null).map((item) => SavedTranslation(id: item.clientRecordId, sourceLanguage: item.sourceLanguage!, targetLanguage: item.targetLanguage!, sourceText: item.sourceText!, translatedText: item.translatedText!, createdAt: item.clientUpdatedAt, updatedAt: item.updatedAt)).toList();
      final deleted = pages.where((item) => item.entityType == 'translation' && item.deleted).map((item) => item.clientRecordId).toList();
      final favorites = pages.where((item) => item.entityType == 'favorite' && !item.deleted && item.translationClientRecordId != null).map((item) => item.translationClientRecordId!).toList();
      await ref.read(localLibraryProvider.notifier).mergeSynced(translations: translations, deletedIds: deleted, favoriteIds: favorites);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppStrings(Localizations.localeOf(context)).saved)));
    } on ApiFailure catch (error) { if (mounted) setState(() => _error = error.message); }
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings(Localizations.localeOf(context));
    final library = ref.watch(localLibraryProvider);
    final queue = ref.watch(syncQueueProvider);
    final records = _records(library);
    return Scaffold(appBar: AppBar(title: Text(strings.cloudSync)), body: _busy && _status == null ? const Center(child: CircularProgressIndicator()) : ListView(padding: const EdgeInsets.all(16), children: [
      Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(strings.cloudSyncBody, style: Theme.of(context).textTheme.bodyMedium), const SizedBox(height: 12), SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(strings.enableCloudSync), value: _status?.enabled ?? false, onChanged: _busy ? null : _toggleConsent), if (_status?.enabled == true) Text(strings.syncConsent, style: Theme.of(context).textTheme.bodySmall), if (queue.pending > 0) Padding(padding: const EdgeInsets.only(top: 10), child: Text('${queue.pending} ${strings.syncPending}', style: TextStyle(color: Theme.of(context).colorScheme.primary))), if (queue.error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(queue.error!, style: TextStyle(color: Theme.of(context).colorScheme.error)))]))),
      if (_error != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
      if (_status?.enabled == true) ...[
        Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(strings.syncPreview, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)), const SizedBox(height: 8), if (records.isEmpty) Text(strings.noLocalRecords) else ...records.map((record) => CheckboxListTile(contentPadding: EdgeInsets.zero, value: _selected.contains(record.clientRecordId), title: Text('${record.entityType} · ${record.clientRecordId}', overflow: TextOverflow.ellipsis), onChanged: (value) => setState(() { if (value == true) { _selected.add(record.clientRecordId); } else { _selected.remove(record.clientRecordId); } }))]),))),
        Wrap(spacing: 10, runSpacing: 10, children: [FilledButton(onPressed: _selected.isEmpty ? null : () => _upload(records), child: Text(strings.uploadSelected)), OutlinedButton(onPressed: _download, child: Text(strings.downloadUpdates)), if (queue.pending > 0) OutlinedButton(onPressed: () { final user = ref.read(authProvider).user; if (user != null) ref.read(syncQueueProvider.notifier).flush(user.id, ref.read(apiClientProvider)); }, child: Text(strings.retry))]),
      ],
    ]));
  }
}
