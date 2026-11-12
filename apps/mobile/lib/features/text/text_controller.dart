import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

const maxTranslationCharacters = 5000;

class TextTranslationState {
  const TextTranslationState({this.source = 'en', this.target = 'my', this.input = '', this.output = '', this.isLoading = false, this.error, this.detectedLanguage});

  final String? source;
  final String target;
  final String input;
  final String output;
  final bool isLoading;
  final ApiFailure? error;
  final String? detectedLanguage;

  TextTranslationState copyWith({Object? source = _unset, String? target, String? input, String? output, bool? isLoading, ApiFailure? error, Object? detectedLanguage = _unset, bool clearError = false}) => TextTranslationState(
        source: source == _unset ? this.source : source as String?,
        target: target ?? this.target,
        input: input ?? this.input,
        output: output ?? this.output,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : error ?? this.error,
        detectedLanguage: detectedLanguage == _unset ? this.detectedLanguage : detectedLanguage as String?,
      );
}

const _unset = Object();

class TextTranslationController extends StateNotifier<TextTranslationState> {
  TextTranslationController(this._client) : super(const TextTranslationState());

  final ApiClient _client;
  int _requestVersion = 0;

  void setSource(String? value) {
    _requestVersion++;
    state = state.copyWith(source: value, output: '', isLoading: false, clearError: true, detectedLanguage: null);
  }

  void setTarget(String value) {
    _requestVersion++;
    state = state.copyWith(target: value, output: '', isLoading: false, clearError: true, detectedLanguage: null);
  }

  void setInput(String value) {
    _requestVersion++;
    final normalized = String.fromCharCodes(value.runes.take(maxTranslationCharacters));
    state = state.copyWith(input: normalized, output: '', isLoading: false, clearError: true, detectedLanguage: null);
  }

  void clear() {
    _requestVersion++;
    state = state.copyWith(input: '', output: '', isLoading: false, clearError: true, detectedLanguage: null);
  }

  void swap() {
    if (state.source == null) return;
    _requestVersion++;
    state = state.copyWith(source: state.target, target: state.source!, output: '', isLoading: false, clearError: true, detectedLanguage: null);
  }

  Future<void> translate() async {
    if (state.input.isEmpty || state.input.runes.length > maxTranslationCharacters || state.source == state.target || state.isLoading) return;
    final version = ++_requestVersion;
    final request = state;
    state = state.copyWith(isLoading: true, output: '', clearError: true, detectedLanguage: null);
    try {
      final result = await _client.translateText(sourceLanguage: request.source, targetLanguage: request.target, text: request.input);
      if (version != _requestVersion) return;
      state = state.copyWith(output: result.translatedText, isLoading: false, detectedLanguage: result.detectedLanguage);
    } on ApiFailure catch (error) {
      if (version != _requestVersion) return;
      state = state.copyWith(isLoading: false, error: error);
    }
  }
}

final textTranslationProvider = StateNotifierProvider.autoDispose<TextTranslationController, TextTranslationState>((ref) => TextTranslationController(ref.watch(apiClientProvider)));
