import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/local_storage/local_library.dart';
import '../../core/localization/app_strings.dart';
import '../../core/theme/app_theme.dart';

class EmptyCollectionPage extends ConsumerWidget {
  const EmptyCollectionPage({super.key, required this.type});
  final String type;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings(Localizations.localeOf(context));
    final library = ref.watch(localLibraryProvider);
    final isHistory = type == 'history';
    final items = isHistory ? library.history : library.favorites;
    final title = isHistory ? strings.history : strings.favorites;
    return Scaffold(appBar: AppBar(title: Text(title)), body: !library.enabled ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [const Icon(Icons.lock_outline_rounded, color: AppTheme.blue, size: 38), const SizedBox(height: 18), Text(strings.localSavingOff, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)), const SizedBox(height: 8), Text(strings.localSavingOffBody, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant))]))) : items.isEmpty ? Center(child: Text(isHistory ? strings.noHistory : strings.noFavorites, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800))) : ListView.separated(padding: const EdgeInsets.all(16), itemCount: items.length, separatorBuilder: (_, __) => const SizedBox(height: 10), itemBuilder: (context, index) { final item = items[index]; return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('${item.sourceLanguage} → ${item.targetLanguage}', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant, fontWeight: FontWeight.w800)), const SizedBox(height: 8), Text(item.sourceText, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)), const SizedBox(height: 8), Text(item.translatedText, style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700))]))); });
  }
}
