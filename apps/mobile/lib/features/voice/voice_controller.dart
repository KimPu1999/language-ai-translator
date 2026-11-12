import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

const maxVoiceCharacters = 5000;
const maxVoiceSeconds = 15;

class VoiceState {
  const VoiceState({this.sourceLocale = 'en-US', this.targetLanguage = 'my', this.voice = '', this.transcript = '', this.translation = '', this.seconds = 0, this.isRecording = false, this.isProcessing = false, this.isTranslating = false, this.isSynthesizing = false, this.isPlaying = false, this.error, this.audioPath});

  final String sourceLocale;
  final String targetLanguage;
  final String voice;
  final String transcript;
  final String translation;
  final int seconds;
  final bool isRecording;
  final bool isProcessing;
  final bool isTranslating;
  final bool isSynthesizing;
  final bool isPlaying;
  final ApiFailure? error;
  final String? audioPath;

  VoiceState copyWith({String? sourceLocale, String? targetLanguage, String? voice, String? transcript, String? translation, int? seconds, bool? isRecording, bool? isProcessing, bool? isTranslating, bool? isSynthesizing, bool? isPlaying, Object? error = _unset, Object? audioPath = _unset}) => VoiceState(
        sourceLocale: sourceLocale ?? this.sourceLocale,
        targetLanguage: targetLanguage ?? this.targetLanguage,
        voice: voice ?? this.voice,
        transcript: transcript ?? this.transcript,
        translation: translation ?? this.translation,
        seconds: seconds ?? this.seconds,
        isRecording: isRecording ?? this.isRecording,
        isProcessing: isProcessing ?? this.isProcessing,
        isTranslating: isTranslating ?? this.isTranslating,
        isSynthesizing: isSynthesizing ?? this.isSynthesizing,
        isPlaying: isPlaying ?? this.isPlaying,
        error: error == _unset ? this.error : error as ApiFailure?,
        audioPath: audioPath == _unset ? this.audioPath : audioPath as String?,
      );
}

const _unset = Object();

class VoiceController extends StateNotifier<VoiceState> {
  VoiceController(this._client) : super(const VoiceState()) {
    _playerStateSubscription = _player.playerStateStream.listen((playerState) {
      if (mounted) state = state.copyWith(isPlaying: playerState.playing);
    });
  }

  final ApiClient _client;
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _player = AudioPlayer();
  StreamSubscription<PlayerState>? _playerStateSubscription;
  Timer? _timer;
  CancelToken? _cancelToken;
  String? _recordingPath;
  String _recordingMimeType = 'audio/webm';
  DateTime? _startedAt;
  int _requestVersion = 0;

  void setSourceLocale(String value) {
    _requestVersion++;
    state = state.copyWith(sourceLocale: value, transcript: '', translation: '', error: null);
  }

  void setTargetLanguage(String value) {
    _requestVersion++;
    state = state.copyWith(targetLanguage: value, translation: '', voice: '', error: null);
  }

  void setVoice(String value) => state = state.copyWith(voice: value, error: null);

  void setTranscript(String value) {
    final normalized = String.fromCharCodes(value.runes.take(maxVoiceCharacters));
    _requestVersion++;
    state = state.copyWith(transcript: normalized, translation: '', error: null);
  }

  Future<void> startRecording() async {
    if (state.isRecording || state.isProcessing) return;
    state = state.copyWith(error: null, transcript: '', translation: '', audioPath: null, seconds: 0);
    try {
      if (!await _recorder.hasPermission()) {
        state = state.copyWith(error: const ApiFailure('MICROPHONE_PERMISSION_DENIED', 'Microphone permission was denied.'));
        return;
      }
      final directory = await getTemporaryDirectory();
      final opusSupported = await _recorder.isEncoderSupported(AudioEncoder.opus);
      final encoder = opusSupported ? AudioEncoder.opus : AudioEncoder.aacLc;
      final extension = opusSupported ? 'webm' : 'm4a';
      _recordingMimeType = opusSupported ? 'audio/webm' : 'audio/mp4';
      final path = '${directory.path}/lingua_voice_${DateTime.now().microsecondsSinceEpoch}.$extension';
      final config = RecordConfig(encoder: encoder, numChannels: 1, sampleRate: 16000);
      await _recorder.start(config, path: path);
      _recordingPath = path;
      _startedAt = DateTime.now();
      state = state.copyWith(isRecording: true, seconds: 0, error: null);
      _timer = Timer.periodic(const Duration(milliseconds: 250), (_) {
        final elapsed = DateTime.now().difference(_startedAt!).inMilliseconds ~/ 1000;
        if (elapsed >= maxVoiceSeconds) {
          unawaited(stopRecording());
        } else if (mounted) {
          state = state.copyWith(seconds: elapsed);
        }
      });
    } catch (_) {
      state = state.copyWith(error: const ApiFailure('RECORDING_UNAVAILABLE', 'The microphone is unavailable.'), isRecording: false);
      await _deleteRecording();
    }
  }

  Future<void> stopRecording() async {
    if (!state.isRecording) return;
    _timer?.cancel();
    _timer = null;
    final version = ++_requestVersion;
    final path = await _recorder.stop();
    _recordingPath = path ?? _recordingPath;
    state = state.copyWith(isRecording: false, isProcessing: true, seconds: state.seconds > maxVoiceSeconds ? maxVoiceSeconds : state.seconds);
    if (_recordingPath == null) {
      state = state.copyWith(isProcessing: false, error: const ApiFailure('EMPTY_RECORDING', 'No audio was recorded.'));
      return;
    }
    _cancelToken = CancelToken();
    try {
      final bytes = await File(_recordingPath!).readAsBytes();
      final result = await _client.transcribeVoice(audioBytes: bytes, locale: state.sourceLocale, mimeType: _recordingMimeType, cancelToken: _cancelToken);
      if (version != _requestVersion || !mounted) return;
      state = state.copyWith(transcript: result.transcript, isProcessing: false, error: null);
    } on ApiFailure catch (error) {
      if (version == _requestVersion && mounted) state = state.copyWith(isProcessing: false, error: error);
    } finally {
      _cancelToken = null;
      await _deleteRecording();
    }
  }

  Future<void> cancelRecording() async {
    _requestVersion++;
    _cancelToken?.cancel('Voice operation cancelled');
    _timer?.cancel();
    _timer = null;
    if (state.isRecording) await _recorder.stop();
    await _deleteRecording();
    await _player.stop();
    if (mounted) state = state.copyWith(isRecording: false, isProcessing: false, isTranslating: false, isSynthesizing: false, isPlaying: false, seconds: 0, error: null);
  }

  Future<void> translate() async {
    if (state.transcript.trim().isEmpty || state.isTranslating || state.isProcessing) return;
    final version = ++_requestVersion;
    final input = state.transcript;
    state = state.copyWith(isTranslating: true, translation: '', error: null);
    try {
      final result = await _client.translateText(sourceLanguage: _textCodeForLocale(state.sourceLocale), targetLanguage: state.targetLanguage, text: input);
      if (version != _requestVersion || !mounted) return;
      state = state.copyWith(translation: result.translatedText, isTranslating: false);
    } on ApiFailure catch (error) {
      if (version == _requestVersion && mounted) state = state.copyWith(isTranslating: false, error: error);
    }
  }

  Future<void> synthesize({required String locale}) async {
    if (state.translation.trim().isEmpty || state.voice.isEmpty || state.isSynthesizing) return;
    final version = ++_requestVersion;
    state = state.copyWith(isSynthesizing: true, error: null);
    try {
      final bytes = await _client.synthesizeVoice(text: state.translation, locale: locale, voice: state.voice);
      if (version != _requestVersion || !mounted) return;
      final directory = await getTemporaryDirectory();
      final path = '${directory.path}/lingua_tts_${DateTime.now().microsecondsSinceEpoch}.wav';
      await _deleteAudio();
      await File(path).writeAsBytes(bytes, flush: true);
      await _player.setFilePath(path);
      state = state.copyWith(audioPath: path, isSynthesizing: false, isPlaying: false);
    } on ApiFailure catch (error) {
      if (version == _requestVersion && mounted) state = state.copyWith(isSynthesizing: false, error: error);
    }
  }

  Future<void> togglePlayback() async {
    if (state.audioPath == null) return;
    if (_player.playing) {
      await _player.pause();
    } else {
      await _player.play();
    }
  }

  Future<void> replay() async {
    if (state.audioPath == null) return;
    await _player.seek(Duration.zero);
    await _player.play();
  }

  Future<void> stopPlayback() async {
    await _player.stop();
    if (mounted) state = state.copyWith(isPlaying: false);
  }

  String? _textCodeForLocale(String locale) => const {'en-US': 'en', 'my-MM': 'my', 'th-TH': 'th', 'zh-CN': 'zh-Hans', 'ja-JP': 'ja', 'ko-KR': 'ko'}[locale];

  Future<void> _deleteRecording() async {
    final path = _recordingPath;
    _recordingPath = null;
    if (path != null) await _deleteFile(path);
  }

  Future<void> _deleteAudio() async {
    final path = state.audioPath;
    if (path != null) await _deleteFile(path);
    if (mounted) state = state.copyWith(audioPath: null, isPlaying: false);
  }

  Future<void> _deleteFile(String path) async {
    try {
      final file = File(path);
      if (await file.exists()) await file.delete();
    } catch (_) {}
  }

  @override
  void dispose() {
    _requestVersion++;
    _cancelToken?.cancel('Voice controller disposed');
    _timer?.cancel();
    unawaited(_recorder.stop());
    unawaited(_deleteRecording());
    unawaited(_player.stop());
    unawaited(_deleteAudio());
    unawaited(_player.dispose());
    unawaited(_playerStateSubscription?.cancel());
    _recorder.dispose();
    super.dispose();
  }
}

final voiceControllerProvider = StateNotifierProvider.autoDispose<VoiceController, VoiceState>((ref) => VoiceController(ref.watch(apiClientProvider)));
