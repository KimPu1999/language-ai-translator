import 'package:flutter/material.dart';

import '../core/localization/app_strings.dart';
import '../core/theme/app_theme.dart';

class FeatureUnavailable extends StatelessWidget {
  const FeatureUnavailable({super.key, required this.icon, required this.title});
  final IconData icon;
  final String title;
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); return Scaffold(appBar: AppBar(title: Text(title)), body: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Container(width: 72, height: 72, decoration: BoxDecoration(color: Theme.of(context).colorScheme.primary.withOpacity(.1), borderRadius: BorderRadius.circular(22)), child: Icon(icon, color: AppTheme.blue, size: 30)), const SizedBox(height: 22), Chip(label: Text(strings.unavailable, style: const TextStyle(fontWeight: FontWeight.w700))), const SizedBox(height: 14), Text('$title is not ready', textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)), const SizedBox(height: 8), Text(strings.unavailableBody, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)), const SizedBox(height: 10), Text('Nothing is recorded or uploaded in Phase 2D.', textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant))]))); }
}

