import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/auth.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

class HistoryPage extends ConsumerStatefulWidget {
  const HistoryPage({super.key});
  @override
  ConsumerState<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends ConsumerState<HistoryPage> {
  late Future<AccountHistoryResponse> _future;
  int _offset = 0;
  static const _limit = 20;
  @override
  void initState() { super.initState(); _future = _load(); }
  Future<AccountHistoryResponse> _load() => ref.read(apiClientProvider).getHistory(limit: _limit, offset: _offset);
  void _reload() => setState(() => _future = _load());
  Future<void> _delete(String id) async { try { await ref.read(apiClientProvider).deleteHistory(id); _reload(); } on ApiFailure catch (error) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message))); } }
  Future<void> _clear() async { final strings = AppStrings(Localizations.localeOf(context)); final confirm = await showDialog<bool>(context: context, builder: (context) => AlertDialog(title: Text(strings.clearAll), content: Text(strings.clearHistoryConfirm), actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: Text(strings.cancel)), FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(strings.clearAll))])); if (confirm != true) return; try { await ref.read(apiClientProvider).clearHistory(); _offset = 0; _reload(); } on ApiFailure catch (error) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message))); } }
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); return Scaffold(appBar: AppBar(title: Text(strings.history), actions: [IconButton(tooltip: strings.clearAll, onPressed: _clear, icon: const Icon(Icons.delete_sweep_outlined))]), body: FutureBuilder<AccountHistoryResponse>(future: _future, builder: (context, snapshot) { if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator()); if (snapshot.hasError) return _HistoryError(error: snapshot.error.toString(), onRetry: _reload); final result = snapshot.data!; if (result.items.isEmpty) return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(strings.noHistory, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)))); return RefreshIndicator(onRefresh: () async => _reload(), child: ListView.separated(padding: const EdgeInsets.all(16), itemCount: result.items.length + 1, separatorBuilder: (_, __) => const SizedBox(height: 10), itemBuilder: (context, index) { if (index == result.items.length) return Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text('${result.offset + 1}–${result.offset + result.items.length} / ${result.total}'), Row(children: [TextButton(onPressed: _offset == 0 ? null : () { _offset -= _limit; _reload(); }, child: Text(strings.previous)), TextButton(onPressed: result.offset + result.items.length >= result.total ? null : () { _offset += _limit; _reload(); }, child: Text(strings.next))])]); final item = result.items[index]; return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('${item.sourceLanguage} → ${item.targetLanguage}', style: Theme.of(context).textTheme.labelSmall?.copyWith(fontWeight: FontWeight.w800, color: Theme.of(context).colorScheme.primary)), const SizedBox(height: 8), Text(item.sourceText, maxLines: 4, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)), const SizedBox(height: 8), Text(item.translatedText, maxLines: 5, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)), Align(alignment: Alignment.centerRight, child: IconButton(tooltip: strings.delete, onPressed: () => _delete(item.id), icon: const Icon(Icons.delete_outline_rounded))) ]))); })); }); }
}

class _HistoryError extends StatelessWidget {
  const _HistoryError({required this.error, required this.onRetry});
  final String error;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Text(error, textAlign: TextAlign.center), const SizedBox(height: 12), OutlinedButton(onPressed: onRetry, child: Text(AppStrings(Localizations.localeOf(context)).retry))])));
}
