import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/theme/app_theme.dart';

class EmptyCollectionPage extends StatelessWidget {
  const EmptyCollectionPage({super.key, required this.type});
  final String type;
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); final isHistory = type == 'history'; final title = isHistory ? 'History' : 'Favorites'; return Scaffold(appBar: AppBar(title: Text(title)), body: Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Container(width: 70, height: 70, decoration: BoxDecoration(color: Theme.of(context).colorScheme.primary.withOpacity(.1), borderRadius: BorderRadius.circular(22)), child: Icon(isHistory ? Icons.history_rounded : Icons.favorite_border_rounded, color: AppTheme.blue, size: 30)), const SizedBox(height: 18), Text(isHistory ? strings.noHistory : strings.noFavorites, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)), const SizedBox(height: 8), Text('Phase 1C does not expose unauthorized user records or claim persistence.', textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant))]))); }
}

