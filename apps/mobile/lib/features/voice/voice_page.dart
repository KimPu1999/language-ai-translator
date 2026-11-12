import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/language.dart';
import '../../core/network/api_client.dart';
import '../../core/models/speech.dart';
import '../../core/providers/app_providers.dart';
import 'voice_controller.dart';

class VoicePage extends ConsumerStatefulWidget {
  const VoicePage({super.key});
  @override
  ConsumerState<VoicePage> createState() => _VoicePageState();
}

class _VoicePageState extends ConsumerState<VoicePage> with WidgetsBindingObserver {
  late final TextEditingController _transcriptController;

  @override
  void initState() {
    super.initState();
    _transcriptController = TextEditingController();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused || state == AppLifecycleState.detached) {
      ref.read(voiceControllerProvider.notifier).cancelRecording();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _transcriptController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings(Localizations.localeOf(context));
    final state = ref.watch(voiceControllerProvider);
    final controller = ref.read(voiceControllerProvider.notifier);
    final languages = ref.watch(languagesProvider);
    final speech = ref.watch(speechCapabilitiesProvider);
    if (_transcriptController.text != state.transcript) {
      _transcriptController.value = TextEditingValue(text: state.transcript, selection: TextSelection.collapsed(offset: state.transcript.length));
    }
    return Scaffold(
      appBar: AppBar(title: Text(strings.voice), actions: [IconButton(tooltip: strings.settings, icon: Icon(Theme.of(context).brightness == Brightness.dark ? Icons.light_mode_rounded : Icons.dark_mode_rounded), onPressed: () => ref.read(themeModeProvider.notifier).state = Theme.of(context).brightness == Brightness.dark ? ThemeMode.light : ThemeMode.dark)]),
      body: speech.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _VoiceError(message: strings.voiceCapabilitiesError, retry: () => ref.invalidate(speechCapabilitiesProvider)),
        data: (capabilities) => RefreshIndicator(onRefresh: () async { ref.invalidate(speechCapabilitiesProvider); await ref.read(speechCapabilitiesProvider.future); }, child: _VoiceContent(strings: strings, state: state, controller: controller, capabilities: capabilities, languages: languages, transcriptController: _transcriptController)),
      ),
    );
  }
}

class _VoiceContent extends StatelessWidget {
  const _VoiceContent({required this.strings, required this.state, required this.controller, required this.capabilities, required this.languages, required this.transcriptController});
  final AppStrings strings;
  final VoiceState state;
  final VoiceController controller;
  final SpeechCapabilities capabilities;
  final AsyncValue<List<Language>> languages;
  final TextEditingController transcriptController;

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, constraints) {
        final sourceOptions = capabilities.languages.where((item) => item.sttEnabled).toList();
        final targetOptions = languages.valueOrNull?.where((item) => item.isTargetEnabled).toList() ?? const <Language>[];
        final source = _firstWhereOrNull(sourceOptions, (item) => item.locale == state.sourceLocale) ?? (sourceOptions.isNotEmpty ? sourceOptions.first : null);
        final target = _firstWhereOrNull(capabilities.languages, (item) => item.textCode == state.targetLanguage);
        final voices = target?.voices ?? const <SpeechVoice>[];
        final selectedVoice = _firstWhereOrNull(voices, (item) => item.name == state.voice) ?? (voices.isNotEmpty ? voices.first : null);
        final available = capabilities.providerConfigured && capabilities.speechRecognition;
        final recorder = _RecorderCard(strings: strings, state: state, controller: controller, available: available);
        final transcript = _TranscriptCard(strings: strings, state: state, controller: controller, transcriptController: transcriptController, target: target, voices: voices, selectedVoice: selectedVoice);
        return ListView(padding: const EdgeInsets.fromLTRB(16, 10, 16, 32), children: [
          Text(strings.voiceTranslator, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -1)),
          const SizedBox(height: 7),
          Text(strings.voiceTranslatorBody, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
          const SizedBox(height: 18),
          if (!capabilities.providerConfigured) _VoiceNotice(text: strings.voiceProviderUnavailable),
          LayoutBuilder(builder: (context, inner) => inner.maxWidth < 540 ? Column(children: [_SourceSelector(strings: strings, state: state, options: sourceOptions, selected: source, controller: controller), const SizedBox(height: 10), _TargetSelector(strings: strings, state: state, options: targetOptions, controller: controller)]) : Row(crossAxisAlignment: CrossAxisAlignment.end, children: [Expanded(child: _SourceSelector(strings: strings, state: state, options: sourceOptions, selected: source, controller: controller)), const SizedBox(width: 12), const Icon(Icons.arrow_forward_rounded, size: 18), const SizedBox(width: 12), Expanded(child: _TargetSelector(strings: strings, state: state, options: targetOptions, controller: controller))])),
          const SizedBox(height: 16),
          if (constraints.maxWidth > 700) Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: recorder), const SizedBox(width: 14), Expanded(child: transcript)]) else Column(children: [recorder, const SizedBox(height: 14), transcript]),
          if (state.audioPath != null) _AudioControls(strings: strings, state: state, controller: controller),
        ]);
      });
}

class _SourceSelector extends StatelessWidget {
  const _SourceSelector({required this.strings, required this.state, required this.options, required this.selected, required this.controller});
  final AppStrings strings;
  final VoiceState state;
  final List<SpeechLanguageCapability> options;
  final SpeechLanguageCapability? selected;
  final VoiceController controller;
  @override
  Widget build(BuildContext context) => DropdownButtonFormField<String>(value: selected?.locale ?? state.sourceLocale, decoration: InputDecoration(labelText: strings.spokenLanguage), items: options.map((item) => DropdownMenuItem(value: item.locale, child: Text('${item.textCode} · ${item.locale}'))).toList(), onChanged: (value) { if (value != null) controller.setSourceLocale(value); });
}

class _TargetSelector extends StatelessWidget {
  const _TargetSelector({required this.strings, required this.state, required this.options, required this.controller});
  final AppStrings strings;
  final VoiceState state;
  final List<Language> options;
  final VoiceController controller;
  @override
  Widget build(BuildContext context) => DropdownButtonFormField<String>(value: options.any((item) => item.code == state.targetLanguage) ? state.targetLanguage : (options.isNotEmpty ? options.first.code : state.targetLanguage), decoration: InputDecoration(labelText: strings.target), items: options.map((item) => DropdownMenuItem(value: item.code, child: Text('${item.name} · ${item.code}'))).toList(), onChanged: (value) { if (value != null) controller.setTargetLanguage(value); });
}

class _RecorderCard extends StatelessWidget {
  const _RecorderCard({required this.strings, required this.state, required this.controller, required this.available});
  final AppStrings strings;
  final VoiceState state;
  final VoiceController controller;
  final bool available;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(children: [Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(strings.recording, style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800, letterSpacing: 1.1)), Text('${formatSeconds(state.seconds)} / 00:15', style: TextStyle(color: state.isRecording ? Colors.redAccent : Theme.of(context).colorScheme.onSurfaceVariant, fontWeight: FontWeight.w700))]), const SizedBox(height: 24), Container(height: 190, width: double.infinity, decoration: BoxDecoration(color: state.isRecording ? Colors.red.withOpacity(.08) : Theme.of(context).colorScheme.primary.withOpacity(.06), borderRadius: BorderRadius.circular(20)), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [IconButton.filled(onPressed: available && !state.isProcessing ? (state.isRecording ? controller.stopRecording : controller.startRecording) : null, iconSize: 32, padding: const EdgeInsets.all(22), tooltip: state.isRecording ? strings.stopRecording : strings.startRecording, icon: Icon(state.isRecording ? Icons.stop_rounded : Icons.mic_none_rounded)), const SizedBox(height: 12), Text(state.isRecording ? strings.recordingNow : strings.pressToRecord, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant))])), const SizedBox(height: 14), if (state.isRecording) OutlinedButton.icon(onPressed: controller.cancelRecording, icon: const Icon(Icons.close_rounded, size: 17), label: Text(strings.cancel)), if (state.isProcessing) const Padding(padding: EdgeInsets.only(top: 12), child: LinearProgressIndicator()), if (state.error != null) Padding(padding: const EdgeInsets.only(top: 14), child: _InlineVoiceError(error: state.error!))])));
}

class _TranscriptCard extends StatelessWidget {
  const _TranscriptCard({required this.strings, required this.state, required this.controller, required this.transcriptController, required this.target, required this.voices, required this.selectedVoice});
  final AppStrings strings;
  final VoiceState state;
  final VoiceController controller;
  final TextEditingController transcriptController;
  final SpeechLanguageCapability? target;
  final List<SpeechVoice> voices;
  final SpeechVoice? selectedVoice;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(strings.transcript, style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800, letterSpacing: 1.1)), Text('${state.transcript.runes.length} / 5,000', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant))]), const SizedBox(height: 12), TextField(controller: transcriptController, onChanged: controller.setTranscript, minLines: 6, maxLines: 8, maxLength: maxVoiceCharacters, decoration: InputDecoration(hintText: strings.transcriptPlaceholder, counterText: '')), const SizedBox(height: 10), SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: state.transcript.trim().isNotEmpty && !state.isTranslating ? controller.translate : null, icon: state.isTranslating ? const SizedBox(width: 17, height: 17, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.translate_rounded, size: 17), label: Text(state.isTranslating ? strings.translating : strings.translate))), if (state.translation.isNotEmpty) ...[const Divider(height: 28), Text(strings.translationResult, style: Theme.of(context).textTheme.labelSmall?.copyWith(fontWeight: FontWeight.w800, color: Theme.of(context).colorScheme.primary)), const SizedBox(height: 8), SelectableText(state.translation, style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.55)), const SizedBox(height: 12), DropdownButtonFormField<String>(value: selectedVoice?.name, decoration: InputDecoration(labelText: strings.voice), items: voices.map((voice) => DropdownMenuItem(value: voice.name, child: Text(voice.name))).toList(), onChanged: (value) { if (value != null) controller.setVoice(value); }), const SizedBox(height: 10), SizedBox(width: double.infinity, child: OutlinedButton.icon(onPressed: selectedVoice != null && target != null && !state.isSynthesizing ? () => controller.synthesize(locale: target.locale) : null, icon: state.isSynthesizing ? const SizedBox(width: 17, height: 17, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.volume_up_outlined, size: 17), label: Text(state.isSynthesizing ? strings.generatingAudio : strings.generateAudio)))])));
}

class _AudioControls extends StatelessWidget {
  const _AudioControls({required this.strings, required this.state, required this.controller});
  final AppStrings strings;
  final VoiceState state;
  final VoiceController controller;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10), child: Row(children: [const Icon(Icons.volume_up_rounded), const SizedBox(width: 10), Expanded(child: Text(strings.audioReady, style: const TextStyle(fontWeight: FontWeight.w700))), IconButton(tooltip: state.isPlaying ? strings.pause : strings.play, onPressed: controller.togglePlayback, icon: Icon(state.isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded)), IconButton(tooltip: strings.replay, onPressed: controller.replay, icon: const Icon(Icons.replay_rounded)), IconButton(tooltip: strings.stop, onPressed: controller.stopPlayback, icon: const Icon(Icons.stop_rounded))])));
}

class _VoiceNotice extends StatelessWidget {
  const _VoiceNotice({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => Container(margin: const EdgeInsets.only(bottom: 14), padding: const EdgeInsets.all(13), decoration: BoxDecoration(color: Colors.amber.withOpacity(.12), border: Border.all(color: Colors.amber.withOpacity(.35)), borderRadius: BorderRadius.circular(16)), child: Text(text, style: const TextStyle(fontWeight: FontWeight.w700)));
}

class _VoiceError extends StatelessWidget {
  const _VoiceError({required this.message, required this.retry});
  final String message;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) => Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: [Text(message, textAlign: TextAlign.center), const SizedBox(height: 14), FilledButton.icon(onPressed: retry, icon: const Icon(Icons.refresh_rounded), label: const Text('Retry'))])));
}

class _InlineVoiceError extends StatelessWidget {
  const _InlineVoiceError({required this.error});
  final ApiFailure error;
  @override
  Widget build(BuildContext context) => Text(error.message, style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 12));
}

String formatSeconds(int value) => '00:${value.toString().padLeft(2, '0')}';

T? _firstWhereOrNull<T>(Iterable<T> values, bool Function(T value) test) {
  for (final value in values) {
    if (test(value)) return value;
  }
  return null;
}
