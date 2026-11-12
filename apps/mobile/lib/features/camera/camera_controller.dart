import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image/image.dart' as img;
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';

import '../../core/models/ocr.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

const maxOcrUploadBytes = 8 * 1024 * 1024;
const maxOcrPixels = 20 * 1000 * 1000;
const maxOcrCharacters = 5000;

enum CameraStage { idle, preparing, previewing, scanning, reviewing, translating, error }

class CameraState {
  const CameraState({this.imagePath, this.sourceLanguage = 'en', this.targetLanguage = 'my', this.cloudConsent = false, this.rotation = 0, this.cropLeft = 0, this.cropTop = 0, this.cropWidth = 1, this.cropHeight = 1, this.text = '', this.translation = '', this.blocks = const [], this.stage = CameraStage.idle, this.error});

  final String? imagePath;
  final String sourceLanguage;
  final String targetLanguage;
  final bool cloudConsent;
  final int rotation;
  final double cropLeft;
  final double cropTop;
  final double cropWidth;
  final double cropHeight;
  final String text;
  final String translation;
  final List<OcrBlock> blocks;
  final CameraStage stage;
  final ApiFailure? error;

  bool get busy => stage == CameraStage.preparing || stage == CameraStage.scanning || stage == CameraStage.translating;

  CameraState copyWith({Object? imagePath = _unset, String? sourceLanguage, String? targetLanguage, bool? cloudConsent, int? rotation, double? cropLeft, double? cropTop, double? cropWidth, double? cropHeight, String? text, String? translation, List<OcrBlock>? blocks, CameraStage? stage, Object? error = _unset}) => CameraState(
        imagePath: imagePath == _unset ? this.imagePath : imagePath as String?,
        sourceLanguage: sourceLanguage ?? this.sourceLanguage,
        targetLanguage: targetLanguage ?? this.targetLanguage,
        cloudConsent: cloudConsent ?? this.cloudConsent,
        rotation: rotation ?? this.rotation,
        cropLeft: cropLeft ?? this.cropLeft,
        cropTop: cropTop ?? this.cropTop,
        cropWidth: cropWidth ?? this.cropWidth,
        cropHeight: cropHeight ?? this.cropHeight,
        text: text ?? this.text,
        translation: translation ?? this.translation,
        blocks: blocks ?? this.blocks,
        stage: stage ?? this.stage,
        error: error == _unset ? this.error : error as ApiFailure?,
      );
}

const _unset = Object();

class CameraOcrController extends StateNotifier<CameraState> {
  CameraOcrController(this._client) : super(const CameraState());

  final ApiClient _client;
  CancelToken? _cancelToken;
  int _version = 0;
  String? _ownedPath;

  void setSourceLanguage(String value) => state = state.copyWith(sourceLanguage: value, error: null, text: '', translation: '', blocks: const [], stage: CameraStage.previewing);
  void setTargetLanguage(String value) => state = state.copyWith(targetLanguage: value, error: null, translation: '');
  void setCloudConsent(bool value) => state = state.copyWith(cloudConsent: value, error: null);
  void rotate() => state = state.copyWith(rotation: (state.rotation + 90) % 360, error: null);
  void setCrop({required double left, required double top, required double width, required double height}) => state = state.copyWith(cropLeft: left.clamp(0, .9).toDouble(), cropTop: top.clamp(0, .9).toDouble(), cropWidth: width.clamp(.1, 1).toDouble(), cropHeight: height.clamp(.1, 1).toDouble());
  void setText(String value) => state = state.copyWith(text: _limit(value), translation: '', error: null, stage: CameraStage.reviewing);

  Future<void> loadImage(String sourcePath) async {
    await _deleteOwnedFile();
    state = state.copyWith(imagePath: null, stage: CameraStage.preparing, error: null, text: '', translation: '', blocks: const []);
    try {
      final source = File(sourcePath);
      if (!await source.exists()) throw const ApiFailure('IMAGE_NOT_FOUND', 'The selected image could not be opened.');
      final bytes = await source.readAsBytes();
      _validate(bytes, sourcePath);
      final directory = await getTemporaryDirectory();
      final extension = path.extension(sourcePath).toLowerCase() == '.png' ? '.png' : '.jpg';
      final owned = File('${directory.path}/lingua_ocr_${DateTime.now().microsecondsSinceEpoch}$extension');
      await owned.writeAsBytes(bytes, flush: true);
      _ownedPath = owned.path;
      state = state.copyWith(imagePath: owned.path, stage: CameraStage.previewing, error: null);
    } on ApiFailure catch (error) {
      state = state.copyWith(stage: CameraStage.error, error: error);
    } catch (_) {
      state = state.copyWith(stage: CameraStage.error, error: const ApiFailure('INVALID_IMAGE', 'This image could not be decoded.'));
    }
  }

  Future<void> scan() async {
    final imagePath = state.imagePath;
    if (imagePath == null || state.busy) return;
    final version = ++_version;
    state = state.copyWith(stage: CameraStage.scanning, error: null, text: '', translation: '', blocks: const []);
    _cancelToken?.cancel('replaced');
    _cancelToken = CancelToken();
    String? preparedPath;
    try {
      preparedPath = await _prepareImage(imagePath);
      final result = await _client.extractOcr(imagePath: preparedPath, language: state.sourceLanguage, cloudConsent: state.cloudConsent, cancelToken: _cancelToken);
      if (version != _version || !mounted) return;
      state = state.copyWith(text: _limit(result.text), blocks: result.blocks, stage: CameraStage.reviewing, error: null);
    } on ApiFailure catch (error) {
      if (version == _version && mounted) state = state.copyWith(stage: CameraStage.error, error: error);
    } catch (_) {
      if (version == _version && mounted) state = state.copyWith(stage: CameraStage.error, error: const ApiFailure('OCR_FAILED', 'Text could not be extracted from this image.'));
    } finally {
      _cancelToken = null;
      if (preparedPath != null && preparedPath != imagePath) await _deleteFile(preparedPath);
    }
  }

  Future<void> translate() async {
    if (state.text.trim().isEmpty || state.busy) return;
    final version = ++_version;
    state = state.copyWith(stage: CameraStage.translating, translation: '', error: null);
    try {
      final result = await _client.translateText(sourceLanguage: state.sourceLanguage, targetLanguage: state.targetLanguage, text: state.text);
      if (version == _version && mounted) state = state.copyWith(translation: result.translatedText, stage: CameraStage.reviewing, error: null);
    } on ApiFailure catch (error) {
      if (version == _version && mounted) state = state.copyWith(stage: CameraStage.error, error: error);
    }
  }

  Future<void> clear() async {
    _version++;
    _cancelToken?.cancel('cleared');
    await _deleteOwnedFile();
    if (mounted) state = const CameraState();
  }

  void _validate(Uint8List bytes, String sourcePath) {
    if (bytes.length > maxOcrUploadBytes) throw const ApiFailure('IMAGE_TOO_LARGE', 'Images must be 8 MB or smaller.');
    final lower = sourcePath.toLowerCase();
    final jpeg = bytes.length >= 3 && bytes[0] == 0xff && bytes[1] == 0xd8 && bytes[2] == 0xff;
    final png = bytes.length >= 8 && bytes[0] == 0x89 && bytes[1] == 0x50 && bytes[2] == 0x4e && bytes[3] == 0x47;
    final webp = bytes.length >= 12 && String.fromCharCodes(bytes.sublist(0, 4)) == 'RIFF' && String.fromCharCodes(bytes.sublist(8, 12)) == 'WEBP';
    if ((!jpeg && !png && !webp) || !(lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.png') || lower.endsWith('.webp'))) throw const ApiFailure('UNSUPPORTED_IMAGE', 'Use a JPEG, PNG, or WebP image.');
    final decoded = img.decodeImage(bytes);
    if (decoded == null || decoded.width == 0 || decoded.height == 0) throw const ApiFailure('INVALID_IMAGE', 'This image could not be decoded.');
    if (decoded.width * decoded.height > maxOcrPixels) throw const ApiFailure('IMAGE_TOO_LARGE', 'Images must contain 20 megapixels or fewer.');
  }

  Future<String> _prepareImage(String sourcePath) async {
    if (state.rotation == 0 && state.cropLeft == 0 && state.cropTop == 0 && state.cropWidth == 1 && state.cropHeight == 1) return sourcePath;
    final bytes = await File(sourcePath).readAsBytes();
    var decoded = img.decodeImage(bytes);
    if (decoded == null) throw const ApiFailure('INVALID_IMAGE', 'This image could not be decoded.');
    decoded = img.bakeOrientation(decoded);
    if (state.rotation != 0) decoded = img.copyRotate(decoded, angle: state.rotation);
    final x = (decoded.width * state.cropLeft).round().clamp(0, decoded.width - 1).toInt();
    final y = (decoded.height * state.cropTop).round().clamp(0, decoded.height - 1).toInt();
    final width = (decoded.width * state.cropWidth).round().clamp(1, decoded.width - x).toInt();
    final height = (decoded.height * state.cropHeight).round().clamp(1, decoded.height - y).toInt();
    decoded = img.copyCrop(decoded, x: x, y: y, width: width, height: height);
    final directory = await getTemporaryDirectory();
    final target = File('${directory.path}/lingua_ocr_prepared_${DateTime.now().microsecondsSinceEpoch}.jpg');
    await target.writeAsBytes(img.encodeJpg(decoded, quality: 90), flush: true);
    return target.path;
  }

  String _limit(String value) => String.fromCharCodes(value.runes.take(maxOcrCharacters));
  Future<void> _deleteOwnedFile() async { final path = _ownedPath; _ownedPath = null; if (path != null) await _deleteFile(path); }
  Future<void> _deleteFile(String filePath) async { try { final file = File(filePath); if (await file.exists()) await file.delete(); } catch (_) {} }

  @override
  void dispose() { _version++; _cancelToken?.cancel('disposed'); unawaited(_deleteOwnedFile()); super.dispose(); }
}

final cameraOcrControllerProvider = StateNotifierProvider.autoDispose<CameraOcrController, CameraState>((ref) => CameraOcrController(ref.watch(apiClientProvider)));
