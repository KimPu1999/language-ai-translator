import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';

class TextTranslationState {
  const TextTranslationState({this.source = 'en', this.target = 'my', this.input = '', this.output = '', this.isLoading = false, this.error});

  final String source;
  final String target;
  final String input;
  final String output;
  final bool isLoading;
  final ApiFailure? error;

  TextTranslationState copyWith({String? source, String? target, String? input, String? output, bool? isLoading, ApiFailure? error, bool clearError = false}) => TextTranslationState(source: source ?? this.source, target: target ?? this.target, input: input ?? this.input, output: output ?? this.output, isLoading: isLoading ?? this.isLoading, error: clearError ? null : error ?? this.error);
}

class TextTranslationController extends StateNotifier<TextTranslationState> {
  TextTranslationController(this._client) : super(const TextTranslationState());

  final ApiClient _client;

  void setSource(String value) => state = state.copyWith(source: value, output: '', clearError: true);
  void setTarget(String value) => state = state.copyWith(target: value, output: '', clearError: true);
  void setInput(String value) => state = state.copyWith(input: value.length > 5000 ? value.substring(0, 5000) : value, output: '', clearError: true);
  void swap() => state = state.copyWith(source: state.target, target: state.source, clearError: true);

  Future<void> translate() async {
    if (state.input.isEmpty || state.input.length > 5000 || state.source == state.target) return;
    state = state.copyWith(isLoading: true, output: '', clearError: true);
    try {
      final result = await _client.translateText(sourceLanguage: state.source, targetLanguage: state.target, text: state.input);
      state = state.copyWith(output: result['translated_text'] as String? ?? '', isLoading: false);
    } on ApiFailure catch (error) {
      state = state.copyWith(isLoading: false, error: error);
    }
  }
}

final textTranslationProvider = StateNotifierProvider.autoDispose<TextTranslationController, TextTranslationState>((ref) => TextTranslationController(ref.watch(apiClientProvider)));

