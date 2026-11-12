import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/language.dart';
import '../../core/providers/app_providers.dart';
import 'camera_controller.dart';

class CameraPage extends ConsumerStatefulWidget {
  const CameraPage({super.key});
  @override
  ConsumerState<CameraPage> createState() => _CameraPageState();
}

class _CameraPageState extends ConsumerState<CameraPage> with WidgetsBindingObserver {
  final _picker = ImagePicker();
  late final TextEditingController _textController;
  CameraController? _nativeCamera;
  Future<void>? _cameraSetup;

  @override
  void initState() { super.initState(); _textController = TextEditingController(); WidgetsBinding.instance.addObserver(this); }
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) { if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused || state == AppLifecycleState.detached) unawaited(_closeCamera()); }

  Future<void> _openCamera() async { if (_nativeCamera != null) return; setState(() => _cameraSetup = _initializeCamera()); final setup = _cameraSetup; if (setup != null) await setup; }
  Future<void> _initializeCamera() async {
    final s = Localizations.of<AppStrings>(context, AppStrings)!;
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) throw CameraException('NoCamera', 'No camera is available.');
      final selected = cameras.firstWhere((item) => item.lensDirection == CameraLensDirection.back, orElse: () => cameras.first);
      final controller = CameraController(selected, ResolutionPreset.medium, enableAudio: false, imageFormatGroup: ImageFormatGroup.jpeg);
      await controller.initialize();
      if (!mounted) { await controller.dispose(); return; }
      setState(() => _nativeCamera = controller);
    } on CameraException catch (error) { if (mounted) _showError(error.code.toLowerCase().contains('denied') ? s.cameraPermissionDenied : s.cameraUnavailable); }
    catch (_) { if (mounted) _showError(s.cameraUnavailable); }
  }
  Future<void> _capture() async {
    final controller = _nativeCamera;
    if (controller == null || !controller.value.isInitialized || controller.value.isTakingPicture) return;
    try { final file = await controller.takePicture(); await _closeCamera(); if (mounted) await ref.read(cameraOcrControllerProvider.notifier).loadImage(file.path); try { await File(file.path).delete(); } catch (_) {} }
    catch (_) { if (mounted) _showError(Localizations.of<AppStrings>(context, AppStrings)!.cameraUnavailable); }
  }
  Future<void> _chooseGallery() async {
    try { final file = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 4096, maxHeight: 4096); if (file != null && mounted) await ref.read(cameraOcrControllerProvider.notifier).loadImage(file.path); }
    catch (_) { if (mounted) _showError(Localizations.of<AppStrings>(context, AppStrings)!.unsupportedImage); }
  }
  Future<void> _closeCamera() async { final controller = _nativeCamera; _nativeCamera = null; _cameraSetup = null; if (mounted) setState(() {}); await controller?.dispose(); }
  void _showError(String message) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));

  @override
  Widget build(BuildContext context) {
    final s = Localizations.of<AppStrings>(context, AppStrings)!;
    final state = ref.watch(cameraOcrControllerProvider);
    final notifier = ref.read(cameraOcrControllerProvider.notifier);
    final capability = ref.watch(ocrCapabilitiesProvider);
    final languages = ref.watch(languagesProvider).valueOrNull ?? const <Language>[];
    final ocrLanguages = capability.valueOrNull?.languages ?? const <String>[];
    final targets = languages.where((item) => item.isTargetEnabled).toList();
    final cloudConsentRequired = capability.valueOrNull?.consentRequired == true;
    final canScan = state.imagePath != null && !state.busy && capability.valueOrNull?.providerConfigured == true && ocrLanguages.contains(state.sourceLanguage) && (!cloudConsentRequired || state.cloudConsent);
    return Scaffold(
      appBar: AppBar(title: Text(s.cameraTitle), actions: [IconButton(onPressed: state.imagePath == null ? null : notifier.clear, tooltip: s.cameraClear, icon: const Icon(Icons.refresh))]),
      body: SafeArea(child: LayoutBuilder(builder: (context, constraints) {
        final wide = constraints.maxWidth >= 760;
        final content = <Widget>[_intro(s), capability.when(loading: () => const LinearProgressIndicator(), error: (_, __) => _notice(Icons.cloud_off_outlined, s.cameraCapabilitiesError), data: (data) => data.providerConfigured && data.languages.isNotEmpty ? const SizedBox.shrink() : _notice(Icons.lock_outline, s.ocrProviderUnavailable)), if (cloudConsentRequired) _cloudConsent(s, state, notifier), _selectors(s, state, notifier, ocrLanguages, targets), if (_nativeCamera != null) _cameraView(s) else _sourceActions(s, state), if (state.imagePath != null) ...[_preview(s, state, notifier), _editor(s, state, notifier, canScan)], if (state.translation.isNotEmpty) _translation(s, state)] ;
        final left = content.take(4).toList();
        final right = content.skip(4).toList();
        return Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 1120), child: Padding(padding: const EdgeInsets.all(20), child: wide ? Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: ListView(shrinkWrap: true, children: left)), const SizedBox(width: 20), Expanded(child: ListView(shrinkWrap: true, children: right))]) : ListView(children: content))));
      })),
    );
  }
  Widget _intro(AppStrings s) => Padding(padding: const EdgeInsets.only(bottom: 16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(s.cameraTitle, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)), const SizedBox(height: 6), Text(s.cameraBody)]));
  Widget _notice(IconData icon, String text) => Card(child: ListTile(leading: Icon(icon), title: Text(text)));
  Widget _cloudConsent(AppStrings s, CameraState state, CameraOcrController notifier) => Card(color: Theme.of(context).colorScheme.tertiaryContainer, child: CheckboxListTile(value: state.cloudConsent, onChanged: (value) => notifier.setCloudConsent(value ?? false), title: Text(s.ocrCloudConsent), controlAffinity: ListTileControlAffinity.leading));
  Widget _selectors(AppStrings s, CameraState state, CameraOcrController notifier, List<String> ocrLanguages, List<Language> targets) => Card(child: Padding(padding: const EdgeInsets.all(16), child: Wrap(spacing: 12, runSpacing: 12, children: [SizedBox(width: 250, child: _dropdown(label: s.ocrLanguage, value: ocrLanguages.contains(state.sourceLanguage) ? state.sourceLanguage : null, items: ocrLanguages, onChanged: (value) { if (value != null) notifier.setSourceLanguage(value); })), SizedBox(width: 250, child: _dropdown(label: s.target, value: targets.any((item) => item.code == state.targetLanguage) ? state.targetLanguage : null, items: targets.map((item) => item.code).toList(), labels: {for (final item in targets) item.code: '${item.name} · ${item.code}'}, onChanged: (value) { if (value != null) notifier.setTargetLanguage(value); }))])));
  Widget _dropdown({required String label, required String? value, required List<String> items, Map<String, String>? labels, required ValueChanged<String?> onChanged}) => DropdownButtonFormField<String>(value: value, decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()), items: items.map((item) => DropdownMenuItem(value: item, child: Text(labels?[item] ?? item))).toList(), onChanged: items.isEmpty ? null : onChanged);
  Widget _sourceActions(AppStrings s, CameraState state) => Card(child: Padding(padding: const EdgeInsets.all(16), child: Wrap(spacing: 12, runSpacing: 12, children: [FilledButton.icon(onPressed: state.busy ? null : _openCamera, icon: const Icon(Icons.camera_alt_outlined), label: Text(s.useCamera)), OutlinedButton.icon(onPressed: state.busy ? null : _chooseGallery, icon: const Icon(Icons.photo_library_outlined), label: Text(s.chooseFromGallery))])));
  Widget _cameraView(AppStrings s) { final controller = _nativeCamera!; return Card(child: Column(children: [AspectRatio(aspectRatio: controller.value.aspectRatio, child: CameraPreview(controller)), Padding(padding: const EdgeInsets.all(12), child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [FilledButton.icon(onPressed: _capture, icon: const Icon(Icons.circle), label: Text(s.takePhoto)), const SizedBox(width: 12), OutlinedButton(onPressed: _closeCamera, child: Text(s.cancel))]))])); }
  Widget _preview(AppStrings s, CameraState state, CameraOcrController notifier) => Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(s.imagePreview, style: Theme.of(context).textTheme.titleMedium), const SizedBox(height: 10), Stack(children: [ClipRect(child: Transform.rotate(angle: state.rotation * 3.1415926535 / 180, child: Image.file(File(state.imagePath!), height: 260, width: double.infinity, fit: BoxFit.contain, errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_outlined, size: 80)))), ...state.blocks.map((block) => Positioned(left: block.left * 300, top: block.top * 260, width: block.width * 300, height: block.height * 260, child: IgnorePointer(child: Container(decoration: BoxDecoration(border: Border.all(color: Theme.of(context).colorScheme.primary))))))]), const SizedBox(height: 8), Wrap(spacing: 8, children: [OutlinedButton.icon(onPressed: state.busy ? null : notifier.rotate, icon: const Icon(Icons.rotate_right), label: Text(s.rotate)), OutlinedButton.icon(onPressed: state.busy ? null : notifier.clear, icon: const Icon(Icons.delete_outline), label: Text(s.removeImage))]), ExpansionTile(title: Text(s.crop), children: [ _cropSlider('Left', state.cropLeft, (value) => notifier.setCrop(left: value, top: state.cropTop, width: state.cropWidth, height: state.cropHeight)), _cropSlider('Top', state.cropTop, (value) => notifier.setCrop(left: state.cropLeft, top: value, width: state.cropWidth, height: state.cropHeight)), _cropSlider('Width', state.cropWidth, (value) => notifier.setCrop(left: state.cropLeft, top: state.cropTop, width: value, height: state.cropHeight)), _cropSlider('Height', state.cropHeight, (value) => notifier.setCrop(left: state.cropLeft, top: state.cropTop, width: state.cropWidth, height: value))])])));

  Widget _cropSlider(String label, double value, ValueChanged<double> onChanged) => Row(children: [SizedBox(width: 64, child: Text(label)), Expanded(child: Slider(value: value.clamp(.1, 1).toDouble(), min: .1, max: 1, onChanged: stateBusy ? null : onChanged))]);
  bool get stateBusy => ref.read(cameraOcrControllerProvider).busy;
  Widget _editor(AppStrings s, CameraState state, CameraOcrController notifier, bool canScan) {
    if (_textController.text != state.text) { _textController.value = TextEditingValue(text: state.text, selection: TextSelection.collapsed(offset: state.text.length)); }
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(s.extractedText, style: Theme.of(context).textTheme.titleMedium), const SizedBox(height: 4), Text(s.reviewText, style: Theme.of(context).textTheme.bodySmall), const SizedBox(height: 10), TextField(key: const Key('ocr-text-editor'), controller: _textController, onChanged: notifier.setText, maxLines: 7, maxLength: maxOcrCharacters, decoration: InputDecoration(hintText: s.extractedText, border: const OutlineInputBorder())), const SizedBox(height: 8), if (state.stage == CameraStage.scanning) const LinearProgressIndicator(), if (state.error != null) Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(state.error!.message, style: TextStyle(color: Theme.of(context).colorScheme.error))), Wrap(spacing: 8, runSpacing: 8, children: [OutlinedButton.icon(onPressed: state.text.isEmpty ? null : () => Clipboard.setData(ClipboardData(text: state.text)), icon: const Icon(Icons.copy_outlined), label: Text(s.copy)), FilledButton.icon(onPressed: canScan ? notifier.scan : null, icon: const Icon(Icons.document_scanner_outlined), label: Text(state.stage == CameraStage.scanning ? s.scanning : s.scanText)), FilledButton.icon(onPressed: state.text.trim().isEmpty || state.busy ? null : notifier.translate, icon: const Icon(Icons.translate), label: Text(s.translateReviewed))])])));
  }
  Widget _translation(AppStrings s, CameraState state) => Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(s.translationResult, style: Theme.of(context).textTheme.titleMedium), const SizedBox(height: 8), SelectableText(state.translation), const SizedBox(height: 10), Wrap(spacing: 8, children: [OutlinedButton.icon(onPressed: () => Clipboard.setData(ClipboardData(text: state.translation)), icon: const Icon(Icons.copy_outlined), label: Text(s.copy)), OutlinedButton.icon(onPressed: () async { final output = await FilePicker.platform.saveFile(dialogTitle: s.exportTxt, fileName: 'lingua-ocr.txt', type: FileType.custom, allowedExtensions: ['txt']); if (output != null) { try { await File(output).writeAsString(state.translation); if (mounted) _showError(s.copied); } catch (_) { if (mounted) _showError(s.fileExportError); } } }, icon: const Icon(Icons.download_outlined), label: Text(s.exportTxt))])])));
  @override
  void dispose() { WidgetsBinding.instance.removeObserver(this); _textController.dispose(); unawaited(_closeCamera()); super.dispose(); }
}
