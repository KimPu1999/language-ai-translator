import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/document.dart';
import '../../core/models/language.dart';
import '../../core/providers/app_providers.dart';
import '../../core/theme/app_theme.dart';
import '../../core/network/api_client.dart';
import 'documents_controller.dart';

class DocumentsPage extends ConsumerStatefulWidget {
  const DocumentsPage({super.key});
  @override
  ConsumerState<DocumentsPage> createState() => _DocumentsPageState();
}

class _DocumentsPageState extends ConsumerState<DocumentsPage> with WidgetsBindingObserver {
  @override
  void initState() { super.initState(); WidgetsBinding.instance.addObserver(this); }
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = ref.read(documentControllerProvider.notifier);
    if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive || state == AppLifecycleState.detached) {
      controller.pauseForLifecycle();
    } else if (state == AppLifecycleState.resumed) {
      unawaited(controller.resumeFromLifecycle());
    }
  }
  @override
  void dispose() { WidgetsBinding.instance.removeObserver(this); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings(Localizations.localeOf(context));
    final state = ref.watch(documentControllerProvider);
    final controller = ref.read(documentControllerProvider.notifier);
    final languageState = ref.watch(languagesProvider);
    final languages = languageState.valueOrNull ?? const [];
    return Scaffold(
      appBar: AppBar(title: Text(strings.documents), actions: [IconButton(tooltip: strings.isMyanmar ? 'အလင်း/အမှောင်' : 'Toggle theme', icon: Icon(Theme.of(context).brightness == Brightness.dark ? Icons.light_mode_rounded : Icons.dark_mode_rounded), onPressed: () => ref.read(themeModeProvider.notifier).state = Theme.of(context).brightness == Brightness.dark ? ThemeMode.light : ThemeMode.dark)]),
      body: LayoutBuilder(builder: (context, constraints) {
        final wide = constraints.maxWidth >= 720;
        return Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 1040), child: ListView(padding: EdgeInsets.fromLTRB(wide ? 28 : 16, 12, wide ? 28 : 16, 32), children: [
          Text(strings.documentTitle, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 6), Text(strings.documentBody, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, height: 1.45)),
          const SizedBox(height: 18), _LanguageCard(strings: strings, state: state, languages: languages, loading: languageState.isLoading, controller: controller),
          const SizedBox(height: 14),
          if (state.filePath == null && state.job == null) _PickerCard(strings: strings, state: state, controller: controller),
          if (state.filePath != null && state.job == null) _SelectedFileCard(strings: strings, state: state, controller: controller),
          if (state.job != null) _JobCard(strings: strings, state: state, controller: controller),
          if (state.error != null) _ErrorCard(strings: strings, error: state.error!, onRetry: state.job?.status == 'failed' ? controller.retry : null),
        ])));
      }),
    );
  }
}

class _LanguageCard extends StatelessWidget {
  const _LanguageCard({required this.strings, required this.state, required this.languages, required this.loading, required this.controller});
  final AppStrings strings; final DocumentState state; final List<Language> languages; final bool loading; final DocumentController controller;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(16), child: LayoutBuilder(builder: (context, constraints) {
    final fields = [_languageField(strings.source, state.sourceLanguage ?? 'auto', true, loading, strings, languages, controller.setSourceLanguage), const SizedBox(width: 12), _languageField(strings.target, state.targetLanguage, false, loading, strings, languages, (value) { if (value != null) controller.setTargetLanguage(value); })];
    return constraints.maxWidth < 460 ? Column(children: [fields[0], const SizedBox(height: 12), fields[2]]) : Row(children: [Expanded(child: fields[0]), fields[1], Expanded(child: fields[2])]);
  })));
}

Widget _languageField(String label, String value, bool auto, bool loading, AppStrings strings, List<Language> languages, void Function(String?) onChanged) => DropdownButtonFormField<String>(value: value, isExpanded: true, decoration: InputDecoration(labelText: label), items: [if (auto) DropdownMenuItem(value: 'auto', child: Text(strings.isMyanmar ? 'အလိုအလျောက် ရှာဖွေမည်' : 'Auto Detect')), ...languages.map((language) => DropdownMenuItem(value: language.code, child: Text('${language.name} · ${language.code}', overflow: TextOverflow.ellipsis)))], onChanged: loading ? null : onChanged);

class _PickerCard extends StatelessWidget {
  const _PickerCard({required this.strings, required this.state, required this.controller});
  final AppStrings strings; final DocumentState state; final DocumentController controller;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 30), child: Column(children: [Container(width: 58, height: 58, decoration: BoxDecoration(color: Theme.of(context).colorScheme.primary.withOpacity(.1), borderRadius: BorderRadius.circular(18)), child: const Icon(Icons.cloud_upload_outlined, color: AppTheme.blue, size: 28)), const SizedBox(height: 14), Text(strings.chooseDocument, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)), const SizedBox(height: 5), Text(strings.documentFormats, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)), const SizedBox(height: 18), FilledButton.icon(onPressed: state.busy ? null : controller.pickDocument, icon: const Icon(Icons.folder_open_rounded), label: Text(strings.chooseDocument))])));
}

class _SelectedFileCard extends StatelessWidget {
  const _SelectedFileCard({required this.strings, required this.state, required this.controller});
  final AppStrings strings; final DocumentState state; final DocumentController controller;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [const Icon(Icons.description_outlined, color: AppTheme.blue), const SizedBox(width: 10), Expanded(child: Text(state.fileName ?? '', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800))), Text(_bytes(state.fileSize), style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12))]), const SizedBox(height: 14), Row(children: [Expanded(child: FilledButton.icon(onPressed: state.busy ? null : controller.upload, icon: state.stage == DocumentStage.uploading ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.upload_rounded), label: Text(state.stage == DocumentStage.uploading ? '${strings.uploading} ${state.uploadProgress}%' : strings.uploadDocument))), const SizedBox(width: 8), OutlinedButton.icon(onPressed: state.busy ? null : controller.clear, icon: const Icon(Icons.close_rounded), label: Text(strings.clear))]), if (state.stage == DocumentStage.uploading) ...[const SizedBox(height: 12), LinearProgressIndicator(value: state.uploadProgress / 100)]])));
}

class _JobCard extends StatelessWidget {
  const _JobCard({required this.strings, required this.state, required this.controller});
  final AppStrings strings; final DocumentState state; final DocumentController controller;
  @override
  Widget build(BuildContext context) {
    final job = state.job!; final pages = state.pages;
    final canTranslate = job.isReviewable && state.segments.isNotEmpty && state.targetLanguage != state.sourceLanguage && !state.busy;
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [const Icon(Icons.description_outlined, color: AppTheme.blue), const SizedBox(width: 10), Expanded(child: Text(job.originalFilename, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800))), _StatusChip(status: job.status, strings: strings)]),
      const SizedBox(height: 6), Text('${_bytes(job.sizeBytes)} · ${job.documentFormat.toUpperCase()} · ${strings.expires} ${_date(job.expiresAt)}', style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12)),
      const SizedBox(height: 14), Row(children: [Expanded(child: LinearProgressIndicator(value: job.progress / 100)), const SizedBox(width: 10), Text('${job.progress}%')]),
      if (job.status == 'queued' || job.status == 'extracting' || job.status == 'translating' || job.status == 'exporting') Padding(padding: const EdgeInsets.only(top: 8), child: Text(_statusText(job.status, strings), style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant))),
      if (job.status == 'expired') _MessageState(icon: Icons.schedule_outlined, title: strings.documentExpired, body: strings.documentExpiredBody, action: OutlinedButton.icon(onPressed: controller.clear, icon: const Icon(Icons.upload_file_outlined), label: Text(strings.chooseDocument))),
      if (job.status == 'cancelled') _MessageState(icon: Icons.cancel_outlined, title: strings.documentCancelled, body: strings.documentBody, action: OutlinedButton.icon(onPressed: controller.clear, icon: const Icon(Icons.upload_file_outlined), label: Text(strings.chooseDocument))),
      if (job.status == 'failed') Padding(padding: const EdgeInsets.only(top: 14), child: FilledButton.icon(onPressed: controller.retry, icon: const Icon(Icons.refresh_rounded), label: Text(strings.retryDocument))),
      if (job.status != 'expired' && job.status != 'cancelled') ...[
        const SizedBox(height: 18), Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Expanded(child: Text(strings.reviewExtracted, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800))), if (pages.length > 1) _Pager(strings: strings, page: state.activePage, count: pages.length, onPage: controller.setPage)]),
        const SizedBox(height: 4), Text(strings.reviewExtractedBody, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12)), const SizedBox(height: 12),
        _ReviewView(strings: strings, state: state, controller: controller, translated: false),
        if (state.segments.isNotEmpty) ...[
          const SizedBox(height: 12), if (job.isReviewable) Row(children: [Expanded(child: OutlinedButton.icon(onPressed: state.busy ? null : controller.saveReview, icon: const Icon(Icons.check_rounded), label: Text(strings.saveReview))), const SizedBox(width: 8), Expanded(child: FilledButton.icon(onPressed: canTranslate ? controller.translate : null, icon: const Icon(Icons.translate_rounded), label: Text(strings.translateDocument)))]),
          if (job.isActive) Padding(padding: const EdgeInsets.only(top: 10), child: OutlinedButton.icon(onPressed: controller.cancelJob, icon: const Icon(Icons.stop_circle_outlined), label: Text(strings.cancelDocument))),
          if (job.status == 'completed') ...[const SizedBox(height: 12), _ReviewView(strings: strings, state: state, controller: controller, translated: true), const SizedBox(height: 14), _DownloadCard(strings: strings, job: job, controller: controller)],
        ] else if (job.isReviewable) Padding(padding: const EdgeInsets.only(top: 14), child: Text(strings.documentNoText, style: TextStyle(color: Theme.of(context).colorScheme.error))),
      ],
    ])));
  }
}

class _ReviewView extends StatelessWidget {
  const _ReviewView({required this.strings, required this.state, required this.controller, required this.translated});
  final AppStrings strings; final DocumentState state; final DocumentController controller; final bool translated;
  @override
  Widget build(BuildContext context) => Container(decoration: BoxDecoration(border: Border.all(color: Theme.of(context).dividerColor), borderRadius: BorderRadius.circular(16)), padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(translated ? strings.translated : strings.original, style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800, color: Theme.of(context).colorScheme.primary)), const SizedBox(height: 8), if (state.visibleSegments.isEmpty) Text(strings.documentNoText, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)) else ...state.visibleSegments.map((segment) => Padding(padding: const EdgeInsets.only(bottom: 10), child: translated ? SelectableText(segment.translatedText ?? strings.translatingDocument, style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.5)) : TextFormField(key: ValueKey('document-segment-${segment.id}'), initialValue: segment.sourceText, onChanged: (value) => controller.editSegment(segment.id, value), maxLines: null, minLines: 2, enabled: state.job?.isReviewable == true, decoration: InputDecoration(labelText: '${strings.page} ${segment.page ?? segment.index + 1}'))))]));
}

class _DownloadCard extends StatelessWidget {
  const _DownloadCard({required this.strings, required this.job, required this.controller});
  final AppStrings strings; final DocumentJob job; final DocumentController controller;
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Theme.of(context).colorScheme.primary.withOpacity(.08), borderRadius: BorderRadius.circular(16)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(strings.documentReady, style: const TextStyle(fontWeight: FontWeight.w800)), const SizedBox(height: 4), Text(strings.documentDownloadOriginal, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12)), const SizedBox(height: 10), Wrap(spacing: 8, runSpacing: 8, children: [for (final format in const ['pdf', 'docx', 'txt']) OutlinedButton.icon(onPressed: job.documentFormat == format ? () => controller.download(share: false) : null, icon: const Icon(Icons.download_outlined, size: 17), label: Text('${strings.downloadDocument} ${format.toUpperCase()}')), OutlinedButton.icon(onPressed: () => controller.download(share: true), icon: const Icon(Icons.ios_share_outlined, size: 17), label: Text(strings.shareDocument))])]);
}

class _Pager extends StatelessWidget {
  const _Pager({required this.strings, required this.page, required this.count, required this.onPage});
  final AppStrings strings; final int page; final int count; final void Function(int) onPage;
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [IconButton(tooltip: strings.previousPage, onPressed: page > 1 ? () => onPage(page - 1) : null, icon: const Icon(Icons.chevron_left_rounded)), Text('${strings.page} $page / $count', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)), IconButton(tooltip: strings.nextPage, onPressed: page < count ? () => onPage(page + 1) : null, icon: const Icon(Icons.chevron_right_rounded))]);
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status, required this.strings});
  final String status; final AppStrings strings;
  @override
  Widget build(BuildContext context) => Chip(label: Text(_statusText(status, strings), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)), backgroundColor: Theme.of(context).colorScheme.primary.withOpacity(.1), side: BorderSide.none, padding: EdgeInsets.zero);
}

class _MessageState extends StatelessWidget {
  const _MessageState({required this.icon, required this.title, required this.body, required this.action});
  final IconData icon; final String title; final String body; final Widget action;
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(top: 18), child: Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Theme.of(context).colorScheme.error.withOpacity(.07), borderRadius: BorderRadius.circular(14)), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Icon(icon, color: Theme.of(context).colorScheme.error), const SizedBox(width: 10), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w800)), const SizedBox(height: 4), Text(body, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)), const SizedBox(height: 9), action]))])));
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({required this.strings, required this.error, required this.onRetry});
  final AppStrings strings; final ApiFailure error; final VoidCallback? onRetry;
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(top: 14), child: Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Colors.amber.withOpacity(.12), border: Border.all(color: Colors.amber.withOpacity(.35)), borderRadius: BorderRadius.circular(16)), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [const Icon(Icons.warning_amber_rounded, color: Colors.amber), const SizedBox(width: 9), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(strings.documentError, style: const TextStyle(fontWeight: FontWeight.w800)), const SizedBox(height: 4), Text(error.message), if (onRetry != null) TextButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh_rounded, size: 17), label: Text(strings.retryDocument))]))])));
}

String _statusText(String status, AppStrings strings) => switch (status) { 'queued' => strings.queued, 'extracting' => strings.extractingDocument, 'awaiting_review' => strings.awaitingReview, 'translating' => strings.translatingDocument, 'exporting' => strings.exporting, 'completed' => strings.completed, 'failed' => strings.failed, 'cancelled' => strings.cancelled, 'expired' => strings.expired, _ => strings.documentError };
String _bytes(int value) => value < 1024 * 1024 ? '${(value / 1024).ceil()} KB' : '${(value / 1024 / 1024).toStringAsFixed(1)} MB';
String _date(DateTime value) => '${value.day.toString().padLeft(2, '0')}/${value.month.toString().padLeft(2, '0')}/${value.year}';
