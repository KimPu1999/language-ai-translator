import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

const maxTranslationCharacters = 5000;

class TextTranslationState {
  const TextTranslationState({this.source = 'en', this.target = 'my', this.input = '', this.output = '', this.isLoading = false, this.error, this.detectedLanguage, this.serverHistoryId, this.serverFavoriteId});

  final String? source;
  final String target;
  final String input;
  final String output;
  final bool isLoading;
  final ApiFailure? error;
  final String? detectedLanguage;
  final String? serverHistoryId;
  final String? serverFavoriteId;

  TextTranslationState copyWith({Object? source = _unset, String? target, String? input, String? output, bool? isLoading, ApiFailure? error, Object? detectedLanguage = _unset, Object? serverHistoryId = _unset, Object? serverFavoriteId = _unset, bool clearError = false}) => TextTranslationState(
        source: source == _unset ? this.source : source as String?,
        target: target ?? this.target,
        input: input ?? this.input,
        output: output ?? this.output,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : error ?? this.error,
        detectedLanguage: detectedLanguage == _unset ? this.detectedLanguage : detectedLanguage as String?,
        serverHistoryId: serverHistoryId == _unset ? this.serverHistoryId : serverHistoryId as String?,
        serverFavoriteId: serverFavoriteId == _unset ? this.serverFavoriteId : serverFavoriteId as String?,
      );
}

const _unset = Object();

class TextTranslationController extends StateNotifier<TextTranslationState> {
  TextTranslationController(this._client) : super(const TextTranslationState());

  final ApiClient _client;
  int _requestVersion = 0;

  void setSource(String? value) {
    _requestVersion++;
    state = state.copyWith(source: value, output: '', isLoading: false, clearError: true, detectedLanguage: null, serverHistoryId: null, serverFavoriteId: null);
  }

  void setTarget(String value) {
    _requestVersion++;
    state = state.copyWith(target: value, output: '', isLoading: false, clearError: true, detectedLanguage: null, serverHistoryId: null, serverFavoriteId: null);
  }

  void setInput(String value) {
    _requestVersion++;
    final normalized = String.fromCharCodes(value.runes.take(maxTranslationCharacters));
    state = state.copyWith(input: normalized, output: '', isLoading: false, clearError: true, detectedLanguage: null, serverHistoryId: null, serverFavoriteId: null);
  }

  void clear() {
    _requestVersion++;
    state = state.copyWith(input: '', output: '', isLoading: false, clearError: true, detectedLanguage: null, serverHistoryId: null, serverFavoriteId: null);
  }

  void swap() {
    if (state.source == null) return;
    _requestVersion++;
    state = state.copyWith(source: state.target, target: state.source!, output: '', isLoading: false, clearError: true, detectedLanguage: null, serverHistoryId: null, serverFavoriteId: null);
  }

  Future<void> translate() async {
    if (state.input.isEmpty || state.input.runes.length > maxTranslationCharacters || state.source == state.target || state.isLoading) return;
    final version = ++_requestVersion;
    final request = state;
    state = state.copyWith(isLoading: true, output: '', clearError: true, detectedLanguage: null);
    try {
      final result = await _client.translateText(sourceLanguage: request.source, targetLanguage: request.target, text: request.input);
      if (version != _requestVersion) return;
      state = state.copyWith(output: result.translatedText, isLoading: false, detectedLanguage: result.detectedLanguage, serverHistoryId: null, serverFavoriteId: null);
    } on ApiFailure catch (error) {
      if (version != _requestVersion) return;
      state = state.copyWith(isLoading: false, error: error);
    }
  }

  bool _accountBusy = false;

  Future<bool> saveToAccount() async {
    if (_accountBusy || state.output.isEmpty || state.serverHistoryId != null) return state.serverHistoryId != null;
    _accountBusy = true;
    try {
      final item = await _client.saveHistory(sourceLanguage: state.source ?? 'auto', targetLanguage: state.target, sourceText: state.input, translatedText: state.output, provider: 'translation');
      state = state.copyWith(serverHistoryId: item.id, clearError: true);
      return true;
    } on ApiFailure catch (error) {
      state = state.copyWith(error: error);
      return false;
    } finally {
      _accountBusy = false;
    }
  }

  Future<bool> toggleAccountFavorite() async {
    if (_accountBusy || state.serverHistoryId == null) return false;
    _accountBusy = true;
    try {
      if (state.serverFavoriteId != null) {
        await _client.deleteFavorite(state.serverFavoriteId!);
        state = state.copyWith(serverFavoriteId: null, clearError: true);
      } else {
        final favorite = await _client.createFavorite(state.serverHistoryId!);
        state = state.copyWith(serverFavoriteId: favorite.id, clearError: true);
      }
      return true;
    } on ApiFailure catch (error) {
      state = state.copyWith(error: error);
      return false;
    } finally {
      _accountBusy = false;
    }
  }
}

final textTranslationProvider = StateNotifierProvider.autoDispose<TextTranslationController, TextTranslationState>((ref) => TextTranslationController(ref.watch(apiClientProvider)));
