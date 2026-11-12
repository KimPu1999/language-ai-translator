import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/local_storage/local_library.dart';
import '../../core/localization/app_strings.dart';
import '../../core/models/language.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/language_selector.dart';
import 'text_controller.dart';

class TextPage extends ConsumerStatefulWidget {
  const TextPage({super.key});
  @override
  ConsumerState<TextPage> createState() => _TextPageState();
}

class _TextPageState extends ConsumerState<TextPage> {
  late final TextEditingController _inputController;

  @override
  void initState() {
    super.initState();
    _inputController = TextEditingController();
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings(Localizations.localeOf(context));
    final state = ref.watch(textTranslationProvider);
    final controller = ref.read(textTranslationProvider.notifier);
    final languages = ref.watch(languagesProvider);
    final capabilities = ref.watch(capabilitiesProvider);
    final library = ref.watch(localLibraryProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Lingua'), actions: [
        IconButton(tooltip: strings.settings, icon: Icon(Theme.of(context).brightness == Brightness.dark ? Icons.light_mode_rounded : Icons.dark_mode_rounded), onPressed: () => ref.read(themeModeProvider.notifier).state = Theme.of(context).brightness == Brightness.dark ? ThemeMode.light : ThemeMode.dark),
      ]),
      body: RefreshIndicator(
        onRefresh: () async { ref.invalidate(languagesProvider); ref.invalidate(capabilitiesProvider); await ref.read(languagesProvider.future).catchError((_) => <Language>[]); },
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 10, 16, 32), children: [
          Text(strings.translate, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -1)),
          const SizedBox(height: 7),
          Text(strings.isMyanmar ? 'အတွေးများကို ရှင်းလင်းစွာ ဘာသာပြန်ပါ။' : 'Move from thought to meaning with clarity.', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
          const SizedBox(height: 24),
          languages.when(data: (items) => _LanguageControls(strings: strings, state: state, languages: items, onSourceChanged: controller.setSource, onTargetChanged: controller.setTarget, onSwap: controller.swap), loading: () => const LinearProgressIndicator(), error: (_, __) => _InlineError(message: strings.languagesError)),
          const SizedBox(height: 16),
          if (capabilities.hasValue && !capabilities.value!.providerConfigured) _CapabilityNotice(strings: strings),
          _EditorCard(label: strings.source, child: Column(children: [
            TextField(controller: _inputController, onChanged: controller.setInput, maxLines: 7, minLines: 5, maxLength: maxTranslationCharacters, keyboardType: TextInputType.multiline, decoration: InputDecoration(hintText: strings.isMyanmar ? 'စာသားကို ရိုက်ထည့်ပါ…' : 'Type or paste text here…', counterText: '${state.input.runes.length} / 5,000')),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              if (state.input.isNotEmpty) TextButton.icon(onPressed: () { _inputController.clear(); controller.clear(); }, icon: const Icon(Icons.clear_rounded, size: 16), label: Text(strings.clear)) else const SizedBox.shrink(),
              FilledButton.icon(onPressed: state.input.isNotEmpty && state.source != state.target && !state.isLoading ? controller.translate : null, icon: const Icon(Icons.send_rounded, size: 17), label: Text(state.isLoading ? strings.loading : strings.translate)),
            ]),
          ])),
          const SizedBox(height: 14),
          _OutputCard(strings: strings, state: state, library: library, onRetry: controller.translate),
        ]),
      ),
    );
  }
}

class _LanguageControls extends StatelessWidget {
  const _LanguageControls({required this.strings, required this.state, required this.languages, required this.onSourceChanged, required this.onTargetChanged, required this.onSwap});
  final AppStrings strings;
  final TextTranslationState state;
  final List<Language> languages;
  final ValueChanged<String?> onSourceChanged;
  final ValueChanged<String?> onTargetChanged;
  final VoidCallback onSwap;
  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, constraints) {
        final source = LanguageSelector(label: strings.source, value: state.source, languages: languages, autoDetect: true, onChanged: onSourceChanged);
        final target = LanguageSelector(label: strings.target, value: state.target, languages: languages, onChanged: onTargetChanged);
        final swap = IconButton(tooltip: strings.swap, onPressed: state.source == null ? null : onSwap, icon: const Icon(Icons.swap_horiz_rounded));
        if (constraints.maxWidth < 520) return Column(children: [source, const SizedBox(height: 10), Row(children: [Expanded(child: target), swap])]);
        return Row(crossAxisAlignment: CrossAxisAlignment.end, children: [Expanded(child: source), const SizedBox(width: 10), swap, const SizedBox(width: 10), Expanded(child: target)]);
      });
}

class _EditorCard extends StatelessWidget {
  const _EditorCard({required this.label, required this.child});
  final String label;
  final Widget child;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label.toUpperCase(), style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant, fontWeight: FontWeight.w800, letterSpacing: 1.1)), const SizedBox(height: 12), child])));
}

class _OutputCard extends ConsumerWidget {
  const _OutputCard({required this.strings, required this.state, required this.library, required this.onRetry});
  final AppStrings strings;
  final TextTranslationState state;
  final LocalLibraryState library;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final item = state.output.isEmpty ? null : SavedTranslation(id: '${state.source ?? 'auto'}-${state.target}-${state.input}', sourceLanguage: state.source ?? 'auto', targetLanguage: state.target, sourceText: state.input, translatedText: state.output, createdAt: DateTime.now());
    final isFavorite = item != null && library.favorites.any((entry) => entry.id == item.id);
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(strings.target.toUpperCase(), style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant, fontWeight: FontWeight.w800, letterSpacing: 1.1)), Icon(Icons.copy_outlined, size: 18, color: Theme.of(context).colorScheme.onSurfaceVariant)]),
      const SizedBox(height: 12),
      ConstrainedBox(constraints: const BoxConstraints(minHeight: 148), child: state.isLoading ? const Center(child: CircularProgressIndicator()) : state.error != null ? _TranslationError(strings: strings, error: state.error!, onRetry: onRetry) : state.output.isEmpty ? _EmptyOutput(strings: strings) : Align(alignment: Alignment.topLeft, child: SelectableText(state.output, style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.65)))),
      const Divider(height: 26),
      if (state.output.isEmpty) OutlinedButton.icon(onPressed: null, icon: const Icon(Icons.copy_rounded, size: 16), label: Text(strings.copy)) else Wrap(alignment: WrapAlignment.end, spacing: 4, runSpacing: 4, children: [OutlinedButton.icon(onPressed: () { Clipboard.setData(ClipboardData(text: state.output)); ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(strings.copied))); }, icon: const Icon(Icons.copy_rounded, size: 16), label: Text(strings.copy)), if (library.enabled && item != null) ...[OutlinedButton.icon(onPressed: () => ref.read(localLibraryProvider.notifier).save(item!), icon: const Icon(Icons.save_outlined, size: 16), label: Text(strings.saveLocally)), IconButton(tooltip: strings.favorite, onPressed: () => ref.read(localLibraryProvider.notifier).toggleFavorite(item!), icon: Icon(isFavorite ? Icons.favorite_rounded : Icons.favorite_border_rounded, color: isFavorite ? Colors.redAccent : null))]]),
    ])));
  }
}

class _EmptyOutput extends StatelessWidget {
  const _EmptyOutput({required this.strings});
  final AppStrings strings;
  @override
  Widget build(BuildContext context) => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [Container(width: 44, height: 44, decoration: BoxDecoration(color: Theme.of(context).colorScheme.primary.withOpacity(.1), borderRadius: BorderRadius.circular(14)), child: const Icon(Icons.auto_awesome_rounded, color: AppTheme.blue)), const SizedBox(height: 10), Text(strings.emptyOutput, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant))]));
}

class _CapabilityNotice extends StatelessWidget {
  const _CapabilityNotice({required this.strings});
  final AppStrings strings;
  @override
  Widget build(BuildContext context) => Container(margin: const EdgeInsets.only(bottom: 14), padding: const EdgeInsets.all(13), decoration: BoxDecoration(color: Colors.amber.withOpacity(.11), border: Border.all(color: Colors.amber.withOpacity(.35)), borderRadius: BorderRadius.circular(16)), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [const Icon(Icons.info_outline_rounded, size: 18, color: Colors.amber), const SizedBox(width: 9), Expanded(child: Text(strings.providerUnavailable, style: Theme.of(context).textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w700)))]));
}

class _TranslationError extends StatelessWidget {
  const _TranslationError({required this.strings, required this.error, required this.onRetry});
  final AppStrings strings;
  final ApiFailure error;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Colors.amber.withOpacity(.12), border: Border.all(color: Colors.amber.withOpacity(.4)), borderRadius: BorderRadius.circular(16)), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [const Icon(Icons.warning_amber_rounded, color: Colors.amber), const SizedBox(width: 10), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(error.code == 'TRANSLATION_ENGINE_NOT_CONFIGURED' ? strings.providerUnavailable : 'Request unavailable', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800)), const SizedBox(height: 5), Text(error.message, style: Theme.of(context).textTheme.bodySmall), const SizedBox(height: 10), Text(strings.providerBody, style: Theme.of(context).textTheme.bodySmall), TextButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh_rounded, size: 16), label: Text(strings.retry))]))]));
}

class _InlineError extends StatelessWidget {
  const _InlineError({required this.message});
  final String message;
  @override
  Widget build(BuildContext context) => Text(message, style: TextStyle(color: Theme.of(context).colorScheme.error));
}
