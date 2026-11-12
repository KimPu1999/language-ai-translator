import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/models/document.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

const maxDocumentUploadBytes = 10 * 1024 * 1024;
const supportedDocumentExtensions = {'pdf', 'docx', 'txt'};

enum DocumentStage { idle, uploading, queued, extracting, review, translating, exporting, completed, failed, cancelled, expired, error }

class DocumentState {
  const DocumentState({this.filePath, this.fileName, this.fileSize = 0, this.sourceLanguage, this.targetLanguage = 'my', this.job, this.segments = const [], this.stage = DocumentStage.idle, this.uploadProgress = 0, this.activePage = 1, this.error});

  final String? filePath;
  final String? fileName;
  final int fileSize;
  final String? sourceLanguage;
  final String targetLanguage;
  final DocumentJob? job;
  final List<DocumentSegment> segments;
  final DocumentStage stage;
  final int uploadProgress;
  final int activePage;
  final ApiFailure? error;

  bool get busy => const {DocumentStage.uploading, DocumentStage.translating, DocumentStage.exporting}.contains(stage);
  bool get active => job?.isActive ?? false;
  List<int> get pages => segments.map((segment) => segment.page).whereType<int>().toSet().toList()..sort();
  List<DocumentSegment> get visibleSegments {
    final allPages = pages;
    if (allPages.isEmpty) return segments;
    final page = allPages[(activePage - 1).clamp(0, allPages.length - 1)];
    return segments.where((segment) => segment.page == page).toList();
  }

  DocumentState copyWith({Object? filePath = _unset, Object? fileName = _unset, int? fileSize, Object? sourceLanguage = _unset, String? targetLanguage, Object? job = _unset, List<DocumentSegment>? segments, DocumentStage? stage, int? uploadProgress, int? activePage, Object? error = _unset}) => DocumentState(
        filePath: filePath == _unset ? this.filePath : filePath as String?,
        fileName: fileName == _unset ? this.fileName : fileName as String?,
        fileSize: fileSize ?? this.fileSize,
        sourceLanguage: sourceLanguage == _unset ? this.sourceLanguage : sourceLanguage as String?,
        targetLanguage: targetLanguage ?? this.targetLanguage,
        job: job == _unset ? this.job : job as DocumentJob?,
        segments: segments ?? this.segments,
        stage: stage ?? this.stage,
        uploadProgress: uploadProgress ?? this.uploadProgress,
        activePage: activePage ?? this.activePage,
        error: error == _unset ? this.error : error as ApiFailure?,
      );
}

const _unset = Object();

final documentControllerProvider = StateNotifierProvider.autoDispose<DocumentController, DocumentState>((ref) {
  final controller = DocumentController(ref.watch(apiClientProvider));
  ref.onDispose(controller.dispose);
  return controller;
});

class DocumentController extends StateNotifier<DocumentState> {
  DocumentController(this._client) : super(const DocumentState());

  final ApiClient _client;
  CancelToken? _requestToken;
  Timer? _pollTimer;
  bool _polling = false;
  final List<String> _temporaryDownloads = [];

  Future<void> pickDocument() async {
    final result = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: supportedDocumentExtensions.toList(), withData: false);
    final picked = result?.files.single;
    if (picked?.path == null) return;
    await selectPath(picked!.path!);
  }

  Future<void> selectPath(String filePath) async {
    try {
      final file = File(filePath);
      final size = await file.length();
      final extension = path.extension(filePath).replaceFirst('.', '').toLowerCase();
      if (!supportedDocumentExtensions.contains(extension)) throw const ApiFailure('UNSUPPORTED_DOCUMENT_FORMAT', 'Only PDF, DOCX, and TXT documents are supported.');
      if (size == 0) throw const ApiFailure('EMPTY_DOCUMENT', 'The selected document is empty.');
      if (size > maxDocumentUploadBytes) throw const ApiFailure('DOCUMENT_TOO_LARGE', 'Documents must be 10 MB or smaller.');
      final bytes = await file.openRead(0, 4).fold<List<int>>([], (all, chunk) => all..addAll(chunk));
      if (extension == 'pdf' && utf8.decode(bytes, allowMalformed: true) != '%PDF') throw const ApiFailure('DOCUMENT_SIGNATURE_MISMATCH', 'The PDF signature is invalid.');
      if (extension == 'docx' && (bytes.length < 2 || bytes[0] != 0x50 || bytes[1] != 0x4b)) throw const ApiFailure('DOCUMENT_SIGNATURE_MISMATCH', 'The DOCX archive signature is invalid.');
      if (extension == 'txt') {
        try { await file.readAsString(encoding: utf8); } catch (_) { throw const ApiFailure('INVALID_TEXT_ENCODING', 'The TXT file must use UTF-8 encoding.'); }
      }
      _clearRequests();
      state = DocumentState(filePath: filePath, fileName: path.basename(filePath), fileSize: size, sourceLanguage: state.sourceLanguage, targetLanguage: state.targetLanguage);
    } on ApiFailure catch (error) {
      state = state.copyWith(stage: DocumentStage.error, error: error);
    } catch (_) {
      state = state.copyWith(stage: DocumentStage.error, error: const ApiFailure('DOCUMENT_READ_FAILED', 'The selected document could not be opened.'));
    }
  }

  void setSourceLanguage(String? language) => state = state.copyWith(sourceLanguage: language, error: null);
  void setTargetLanguage(String language) => state = state.copyWith(targetLanguage: language, error: null);
  void setPage(int page) => state = state.copyWith(activePage: page);
  void editSegment(String id, String value) => state = state.copyWith(segments: state.segments.map((segment) => segment.id == id ? segment.copyWith(sourceText: value, translatedText: null) : segment).toList(), error: null);

  Future<void> upload() async {
    final filePath = state.filePath;
    if (filePath == null || state.busy) return;
    _clearRequests();
    final requestToken = CancelToken();
    _requestToken = requestToken;
    state = state.copyWith(stage: DocumentStage.uploading, uploadProgress: 0, error: null);
    try {
      final job = await _client.uploadDocument(filePath: filePath, sourceLanguage: state.sourceLanguage, cancelToken: requestToken, onSendProgress: (sent, total) => state = state.copyWith(uploadProgress: total == 0 ? 0 : ((sent / total) * 100).round()));
      if (!mounted) return;
      state = state.copyWith(job: job, stage: _stageFor(job.status), uploadProgress: 100, error: null);
      _startPolling();
    } on ApiFailure catch (error) {
      if (!mounted || requestToken.isCancelled) return;
      state = state.copyWith(stage: DocumentStage.error, error: error);
    } catch (_) {
      state = state.copyWith(stage: DocumentStage.error, error: const ApiFailure('NETWORK_ERROR', 'The document could not be uploaded.'));
    }
  }

  Future<void> saveReview() async {
    final job = state.job;
    if (job == null || !job.isReviewable || state.segments.isEmpty || state.busy) return;
    try {
      final response = await _client.updateDocumentSegments(job.id, _reviewSegments());
      state = state.copyWith(segments: response.segments, error: null);
    } on ApiFailure catch (error) { state = state.copyWith(stage: DocumentStage.error, error: error); }
  }

  Future<void> translate() async {
    final job = state.job;
    if (job == null || !job.isReviewable || state.segments.isEmpty || state.targetLanguage == state.sourceLanguage || state.busy) return;
    try {
      final reviewed = _reviewSegments();
      await _client.updateDocumentSegments(job.id, reviewed);
      final requestToken = CancelToken();
      _requestToken = requestToken;
      final started = await _client.translateDocument(id: job.id, sourceLanguage: state.sourceLanguage, targetLanguage: state.targetLanguage, idempotencyKey: 'mobile-document-${job.id}-${state.sourceLanguage ?? 'auto'}-${state.targetLanguage}', cancelToken: requestToken);
      state = state.copyWith(job: started, stage: _stageFor(started.status), error: null);
      _startPolling();
    } on ApiFailure catch (error) { state = state.copyWith(stage: DocumentStage.error, error: error); }
  }

  Future<void> cancelJob() async {
    final job = state.job;
    if (job == null || !job.isActive) return;
    _clearRequests();
    try {
      final cancelled = await _client.cancelDocument(job.id);
      state = state.copyWith(job: cancelled, stage: _stageFor(cancelled.status), error: null);
    } on ApiFailure catch (error) { state = state.copyWith(stage: DocumentStage.error, error: error); }
  }

  Future<void> retry() async {
    final job = state.job;
    if (job == null || job.status != 'failed') return;
    try {
      final retried = await _client.retryDocument(job.id);
      state = state.copyWith(job: retried, stage: _stageFor(retried.status), error: null);
      _startPolling();
    } on ApiFailure catch (error) { state = state.copyWith(stage: DocumentStage.error, error: error); }
  }

  Future<void> download({required bool share}) async {
    final job = state.job;
    if (job == null || job.status != 'completed') return;
    try {
      final download = await _client.downloadDocument(job.id);
      final directory = await getTemporaryDirectory();
      final temp = File(path.join(directory.path, 'lingua_${DateTime.now().microsecondsSinceEpoch}_${download.filename}'));
      await temp.writeAsBytes(download.bytes, flush: true);
      _temporaryDownloads.add(temp.path);
      if (share) {
        await SharePlus.instance.share(ShareParams(files: [XFile(temp.path)], text: 'Lingua translated document'));
      } else {
        final destination = await FilePicker.platform.saveFile(fileName: download.filename, bytes: Uint8List.fromList(download.bytes));
        if (destination != null && !Platform.isAndroid && !Platform.isIOS) await File(destination).writeAsBytes(download.bytes, flush: true);
      }
    } on ApiFailure catch (error) {
      state = state.copyWith(stage: DocumentStage.error, error: error);
    }
  }

  Future<void> clear() async {
    final id = state.job?.id;
    _clearRequests();
    if (id != null) {
      try { await _client.deleteDocument(id); } catch (_) { /* The server expiration still protects private data. */ }
    }
    await _deleteTemporaryDownloads();
    state = const DocumentState();
  }

  void pauseForLifecycle() { _clearRequests(); }
  Future<void> resumeFromLifecycle() async { if (state.job?.isActive == true) await refresh(); }

  Future<void> refresh() async {
    final job = state.job;
    if (job == null) return;
    try {
      final updated = await _client.getDocument(job.id);
      state = state.copyWith(job: updated, stage: _stageFor(updated.status), error: null);
      if (updated.status == 'awaiting_review' || updated.status == 'translating' || updated.status == 'exporting' || updated.status == 'completed') {
        final segments = await _client.getDocumentSegments(job.id);
        state = state.copyWith(segments: segments.segments);
      }
      if (updated.isActive) _startPolling();
    } on ApiFailure catch (error) { state = state.copyWith(stage: DocumentStage.error, error: error); }
  }

  List<DocumentSegment> _reviewSegments() => state.segments.map((segment) => segment.copyWith(translatedText: null)).toList();
  void _startPolling() {
    if (_polling || state.job?.isActive != true) return;
    _polling = true;
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      if (!mounted || state.job?.isActive != true) { _pollTimer?.cancel(); _polling = false; return; }
      await refresh();
    });
  }
  DocumentStage _stageFor(String status) => switch (status) { 'queued' => DocumentStage.queued, 'extracting' => DocumentStage.extracting, 'awaiting_review' => DocumentStage.review, 'translating' => DocumentStage.translating, 'exporting' => DocumentStage.exporting, 'completed' => DocumentStage.completed, 'failed' => DocumentStage.failed, 'cancelled' => DocumentStage.cancelled, 'expired' => DocumentStage.expired, _ => DocumentStage.error };
  void _clearRequests() { _pollTimer?.cancel(); _pollTimer = null; _polling = false; _requestToken?.cancel(); _requestToken = null; }
  Future<void> _deleteTemporaryDownloads() async { for (final filePath in _temporaryDownloads) { try { await File(filePath).delete(); } catch (_) {} } _temporaryDownloads.clear(); }
  @override
  void dispose() { _clearRequests(); unawaited(_deleteTemporaryDownloads()); super.dispose(); }
}
