import 'package:flutter/material.dart';

import '../core/models/language.dart';

class LanguageSelector extends StatelessWidget {
  const LanguageSelector({super.key, required this.label, required this.value, required this.languages, required this.onChanged});
  final String label;
  final String value;
  final List<Language> languages;
  final ValueChanged<String> onChanged;
  @override
  Widget build(BuildContext context) => Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label.toUpperCase(), style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant, fontWeight: FontWeight.w800, letterSpacing: 1.1)), const SizedBox(height: 7), DropdownButtonFormField<String>(value: languages.any((language) => language.code == value) ? value : null, isExpanded: true, decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 3)), items: languages.map((language) => DropdownMenuItem(value: language.code, child: Text('${language.name} · ${language.code}', overflow: TextOverflow.ellipsis))).toList(), onChanged: (next) { if (next != null) onChanged(next); })]));
}

