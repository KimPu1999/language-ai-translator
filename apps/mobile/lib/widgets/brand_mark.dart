import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.compact = false});
  final bool compact;
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [Container(width: compact ? 34 : 38, height: compact ? 34 : 38, decoration: BoxDecoration(color: AppTheme.navy, borderRadius: BorderRadius.circular(12)), child: const Icon(Icons.auto_awesome_rounded, color: Colors.white, size: 19)), if (!compact) ...[const SizedBox(width: 10), Text('Lingua', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.5))]]);
}

