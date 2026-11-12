import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../../core/local_storage/local_library.dart';
import '../../core/models/speech.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

const maxConversationCharacters = 5000;
const maxConversationSeconds = 15;

enum ConversationStage { idle, recording, transcribing, reviewing, translating, ready, playing, error }

class ConversationProfile {
  const ConversationProfile({required this.sourceLocale, required this.targetLanguage, this.voice = '', this.voiceLocale = ''});
  final String sourceLocale;
  final String targetLanguage;
  final String voice;
  final String voiceLocale;
  ConversationProfile copyWith({String? sourceLocale, String? targetLanguage, String? voice, String? voiceLocale}) => ConversationProfile(sourceLocale: sourceLocale ?? this.sourceLocale, targetLanguage: targetLanguage ?? this.targetLanguage, voice: voice ?? this.voice, voiceLocale: voiceLocale ?? this.voiceLocale);
}

class ConversationTurn {
  const ConversationTurn({required this.id, required this.speaker, required this.profile, this.transcript = '', this.translation = '', this.stage = ConversationStage.idle, this.error, this.audioPath});
  final String id;
  final String speaker;
  final ConversationProfile profile;
  final String transcript;
  final String translation;
  final ConversationStage stage;
  final ApiFailure? error;
  final String? audioPath;
  ConversationTurn copyWith({ConversationProfile? profile, String? transcript, String? translation, ConversationStage? stage, Object? error = _unset, Object? audioPath = _unset}) => ConversationTurn(id: id, speaker: speaker, profile: profile ?? this.profile, transcript: transcript ?? this.transcript, translation: translation ?? this.translation, stage: stage ?? this.stage, error: error == _unset ? this.error : error as ApiFailure?, audioPath: audioPath == _unset ? this.audioPath : audioPath as String?);
}
const _unset = Object();

class ConversationState {
  const ConversationState({this.turns = const [], this.a = const ConversationProfile(sourceLocale: 'en-US', targetLanguage: 'my', voiceLocale: 'my-MM'), this.b = const ConversationProfile(sourceLocale: 'my-MM', targetLanguage: 'en', voiceLocale: 'en-US'), this.activeSpeaker, this.ended = false, this.seconds = 0, this.playingTurnId});
  final List<ConversationTurn> turns;
  final ConversationProfile a;
  final ConversationProfile b;
  final String? activeSpeaker;
  final bool ended;
  final int seconds;
  final String? playingTurnId;
  ConversationState copyWith({List<ConversationTurn>? turns, ConversationProfile? a, ConversationProfile? b, Object? activeSpeaker = _unset, bool? ended, int? seconds, Object? playingTurnId = _unset}) => ConversationState(turns: turns ?? this.turns, a: a ?? this.a, b: b ?? this.b, activeSpeaker: activeSpeaker == _unset ? this.activeSpeaker : activeSpeaker as String?, ended: ended ?? this.ended, seconds: seconds ?? this.seconds, playingTurnId: playingTurnId == _unset ? this.playingTurnId : playingTurnId as String?);
}

class ConversationController extends StateNotifier<ConversationState> {
  ConversationController(this._client, this._library) : super(const ConversationState()) { _playerSubscription = _player.playerStateStream.listen((value) { if (!mounted) return; if (!value.playing && state.playingTurnId != null) { final id = state.playingTurnId!; _update(id, (turn) => turn.copyWith(stage: ConversationStage.ready)); state = state.copyWith(playingTurnId: null); } }); }
  final ApiClient _client;
  final LocalLibraryController _library;
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _player = AudioPlayer();
  StreamSubscription<PlayerState>? _playerSubscription;
  Timer? _timer;
  CancelToken? _cancelToken;
  String? _recordingPath;
  String _mimeType = 'audio/webm';
  DateTime? _startedAt;
  int _version = 0;
  int _counter = 0;

  ConversationProfile profile(String speaker) => speaker == 'A' ? state.a : state.b;
  void setProfile(String speaker, ConversationProfile profile) => state = state.copyWith(a: speaker == 'A' ? profile : null, b: speaker == 'B' ? profile : null);
  void _update(String id, ConversationTurn Function(ConversationTurn) change) => state = state.copyWith(turns: [for (final turn in state.turns) if (turn.id == id) change(turn) else turn]);
  String _id() => 'turn-${DateTime.now().microsecondsSinceEpoch}-${_counter++}';
  String? _textCode(String locale) => const {'en-US': 'en', 'my-MM': 'my', 'th-TH': 'th', 'zh-CN': 'zh-Hans', 'ja-JP': 'ja', 'ko-KR': 'ko'}[locale];

  Future<void> start(String speaker, SpeechCapabilities capabilities) async {
    if (state.ended || state.activeSpeaker != null || state.playingTurnId != null || !capabilities.speechRecognition) return;
    try {
      if (!await _recorder.hasPermission()) { _appendError(speaker, 'MICROPHONE_PERMISSION_DENIED', 'Microphone permission was denied.'); return; }
      final directory = await getTemporaryDirectory(); final opus = await _recorder.isEncoderSupported(AudioEncoder.opus); final path = '${directory.path}/lingua_conversation_${DateTime.now().microsecondsSinceEpoch}.${opus ? 'webm' : 'm4a'}';
      final encoder = opus ? AudioEncoder.opus : AudioEncoder.aacLc; _mimeType = opus ? 'audio/webm' : 'audio/mp4'; await _recorder.start(RecordConfig(encoder: encoder, numChannels: 1, sampleRate: 16000), path: path); _recordingPath = path; _startedAt = DateTime.now(); state = state.copyWith(activeSpeaker: speaker, seconds: 0);
      _timer = Timer.periodic(const Duration(milliseconds: 250), (_) { final seconds = DateTime.now().difference(_startedAt!).inSeconds; if (seconds >= maxConversationSeconds) { unawaited(stop(speaker)); } else if (mounted) state = state.copyWith(seconds: seconds); });
    } catch (_) { _appendError(speaker, 'RECORDING_UNAVAILABLE', 'The microphone is unavailable.'); }
  }

  Future<void> stop(String speaker) async {
    if (state.activeSpeaker != speaker) return; _timer?.cancel(); _timer = null; final version = ++_version; final path = await _recorder.stop(); _recordingPath = path ?? _recordingPath; final filePath = _recordingPath; state = state.copyWith(activeSpeaker: null, seconds: 0); if (filePath == null) return;
    final turn = ConversationTurn(id: _id(), speaker: speaker, profile: profile(speaker), stage: ConversationStage.transcribing); state = state.copyWith(turns: [...state.turns, turn]);
    try { final result = await _client.transcribeVoice(audioBytes: await File(filePath).readAsBytes(), locale: turn.profile.sourceLocale, mimeType: _mimeType, cancelToken: _cancelToken = CancelToken()); if (version != _version || !mounted) return; _update(turn.id, (item) => item.copyWith(transcript: result.transcript, stage: ConversationStage.reviewing)); }
    on ApiFailure catch (error) { if (version == _version && mounted) _update(turn.id, (item) => item.copyWith(stage: ConversationStage.error, error: error)); }
    finally { _cancelToken = null; await _delete(filePath); _recordingPath = null; }
  }

  Future<void> cancel() async { _version++; _cancelToken?.cancel('Conversation cancelled'); _timer?.cancel(); if (state.activeSpeaker != null) await _recorder.stop(); if (_recordingPath != null) await _delete(_recordingPath!); _recordingPath = null; state = state.copyWith(activeSpeaker: null, seconds: 0); }
  void edit(String id, String value) { final text = String.fromCharCodes(value.runes.take(maxConversationCharacters)); _version++; _update(id, (turn) => turn.copyWith(transcript: text, translation: '', stage: ConversationStage.reviewing, error: null)); }
  Future<void> translate(String id) async { final turn = state.turns.firstWhere((item) => item.id == id); if (turn.transcript.trim().isEmpty) return; final version = ++_version; _update(id, (item) => item.copyWith(stage: ConversationStage.translating, translation: '', error: null)); try { final result = await _client.translateText(sourceLanguage: _textCode(turn.profile.sourceLocale), targetLanguage: turn.profile.targetLanguage, text: turn.transcript); if (version != _version || !mounted) return; _update(id, (item) => item.copyWith(translation: result.translatedText, stage: ConversationStage.ready)); } on ApiFailure catch (error) { if (version == _version && mounted) _update(id, (item) => item.copyWith(stage: ConversationStage.error, error: error)); } }
  Future<void> synthesize(String id) async { final turn = state.turns.firstWhere((item) => item.id == id); if (turn.translation.isEmpty || turn.profile.voice.isEmpty || state.playingTurnId != null) return; final version = ++_version; try { final bytes = await _client.synthesizeVoice(text: turn.translation, locale: turn.profile.voiceLocale, voice: turn.profile.voice); if (version != _version || !mounted) return; final directory = await getTemporaryDirectory(); final path = '${directory.path}/lingua_conversation_tts_${DateTime.now().microsecondsSinceEpoch}.wav'; await _delete(turn.audioPath); await File(path).writeAsBytes(bytes, flush: true); await _player.setFilePath(path); _update(id, (item) => item.copyWith(audioPath: path, stage: ConversationStage.playing)); state = state.copyWith(playingTurnId: id); await _player.play(); } on ApiFailure catch (error) { if (version == _version && mounted) _update(id, (item) => item.copyWith(stage: ConversationStage.error, error: error)); } }
  Future<void> togglePlayback(String id) async { if (state.playingTurnId == id) { await _player.pause(); state = state.copyWith(playingTurnId: null); _update(id, (turn) => turn.copyWith(stage: ConversationStage.ready)); return; } final turn = state.turns.firstWhere((item) => item.id == id); if (turn.audioPath == null || state.activeSpeaker != null) return; await _player.setFilePath(turn.audioPath!); state = state.copyWith(playingTurnId: id); _update(id, (item) => item.copyWith(stage: ConversationStage.playing)); await _player.play(); }
  Future<void> replay(String id) async { await _player.stop(); await togglePlayback(id); }
  Future<void> stopPlayback() async { await _player.stop(); if (state.playingTurnId != null) _update(state.playingTurnId!, (turn) => turn.copyWith(stage: ConversationStage.ready)); state = state.copyWith(playingTurnId: null); }
  Future<void> save(String id) async { if (!_library.state.enabled) return; final turn = state.turns.firstWhere((item) => item.id == id); if (turn.translation.isEmpty) return; await _library.save(SavedTranslation(id: turn.id, sourceLanguage: _textCode(turn.profile.sourceLocale) ?? turn.profile.sourceLocale, targetLanguage: turn.profile.targetLanguage, sourceText: turn.transcript, translatedText: turn.translation, createdAt: DateTime.now())); }
  Future<void> end() async { await cancel(); await stopPlayback(); state = state.copyWith(ended: true); }
  Future<void> clear() async { await cancel(); await stopPlayback(); for (final turn in state.turns) { await _delete(turn.audioPath); } state = const ConversationState(); }
  void _appendError(String speaker, String code, String message) => state = state.copyWith(turns: [...state.turns, ConversationTurn(id: _id(), speaker: speaker, profile: profile(speaker), stage: ConversationStage.error, error: ApiFailure(code, message))]);
  Future<void> _delete(String? path) async { if (path == null) return; try { final file = File(path); if (await file.exists()) await file.delete(); } catch (_) {} }
  @override void dispose() { _version++; _cancelToken?.cancel(); _timer?.cancel(); unawaited(_recorder.stop()); unawaited(_delete(_recordingPath)); unawaited(_player.stop()); for (final turn in state.turns) { unawaited(_delete(turn.audioPath)); } unawaited(_player.dispose()); unawaited(_playerSubscription?.cancel()); _recorder.dispose(); super.dispose(); }
}

final conversationControllerProvider = StateNotifierProvider.autoDispose<ConversationController, ConversationState>((ref) => ConversationController(ref.watch(apiClientProvider), ref.watch(localLibraryProvider.notifier)));
