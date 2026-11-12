import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/auth.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

class FavoritesPage extends ConsumerStatefulWidget {
  const FavoritesPage({super.key});
  @override
  ConsumerState<FavoritesPage> createState() => _FavoritesPageState();
}

class _FavoritesPageState extends ConsumerState<FavoritesPage> {
  late Future<FavoritesResponse> _future;
  @override
  void initState() { super.initState(); _future = ref.read(apiClientProvider).getFavorites(); }
  void _reload() => setState(() => _future = ref.read(apiClientProvider).getFavorites());
  Future<void> _delete(String id) async { try { await ref.read(apiClientProvider).deleteFavorite(id); _reload(); } on ApiFailure catch (error) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message))); } }
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); return Scaffold(appBar: AppBar(title: Text(strings.favorites)), body: FutureBuilder<FavoritesResponse>(future: _future, builder: (context, snapshot) { if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator()); if (snapshot.hasError) return Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Text(snapshot.error.toString(), textAlign: TextAlign.center), const SizedBox(height: 12), OutlinedButton(onPressed: _reload, child: Text(strings.retry))]))); final items = snapshot.data!.items; if (items.isEmpty) return Center(child: Text(strings.noFavorites, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800))); return RefreshIndicator(onRefresh: () async => _reload(), child: ListView.separated(padding: const EdgeInsets.all(16), itemCount: items.length, separatorBuilder: (_, __) => const SizedBox(height: 10), itemBuilder: (context, index) { final favorite = items[index]; return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('${favorite.translation.sourceLanguage} → ${favorite.translation.targetLanguage}', style: Theme.of(context).textTheme.labelSmall?.copyWith(fontWeight: FontWeight.w800, color: Theme.of(context).colorScheme.primary)), const SizedBox(height: 8), Text(favorite.translation.translatedText, style: const TextStyle(fontWeight: FontWeight.w700)), Align(alignment: Alignment.centerRight, child: IconButton(tooltip: strings.delete, onPressed: () => _delete(favorite.id), icon: const Icon(Icons.favorite_rounded, color: Colors.redAccent))) ]))); })); }); }
}
