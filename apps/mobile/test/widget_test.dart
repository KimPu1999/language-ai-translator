import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:lingua_mobile/core/localization/app_strings.dart';
import 'package:lingua_mobile/core/models/language.dart';
import 'package:lingua_mobile/core/models/speech.dart';
import 'package:lingua_mobile/core/network/api_client.dart';
import 'package:lingua_mobile/core/models/translation.dart';
import 'package:lingua_mobile/core/providers/app_providers.dart';
import 'package:lingua_mobile/features/text/text_page.dart';
import 'package:lingua_mobile/widgets/feature_unavailable.dart';
import 'package:lingua_mobile/features/text/text_controller.dart';
import 'package:lingua_mobile/features/voice/voice_page.dart';

class _FakeApiClient extends ApiClient {
  @override
  Future<List<Map<String, dynamic>>> getLanguages() async => [
        {'code': 'en', 'name': 'English', 'is_source_enabled': true, 'is_target_enabled': true},
        {'code': 'my', 'name': 'Burmese', 'is_source_enabled': true, 'is_target_enabled': true},
      ];

  @override
  Future<Map<String, dynamic>> getCapabilities() async => {'text_translation': false, 'provider_configured': false, 'supported_operations': ['text_translation']};
}

class _TranslationApiClient extends ApiClient {
  _TranslationApiClient({this.failure});
  final ApiFailure? failure;
  String? receivedSource;
  @override
  Future<TranslationResponse> translateText({required String? sourceLanguage, required String targetLanguage, required String text}) async {
    receivedSource = sourceLanguage;
    if (failure != null) throw failure!;
    return const TranslationResponse(translatedText: 'Hello', provider: 'test');
  }
}

class _VoiceApiClient extends ApiClient {
  @override
  Future<List<Map<String, dynamic>>> getLanguages() async => [
        {'code': 'en', 'name': 'English', 'is_source_enabled': true, 'is_target_enabled': true},
        {'code': 'my', 'name': 'Burmese', 'is_source_enabled': true, 'is_target_enabled': true},
      ];

  @override
  Future<SpeechCapabilities> getSpeechCapabilities() async => SpeechCapabilities.fromJson({
        'provider': 'azure',
        'provider_configured': true,
        'speech_recognition': true,
        'speech_synthesis': true,
        'languages': [
          {'text_code': 'en', 'locale': 'en-US', 'stt_enabled': true, 'tts_enabled': true, 'voices': [{'name': 'en-US-JennyNeural', 'locale': 'en-US', 'gender': 'Female'}]},
          {'text_code': 'my', 'locale': 'my-MM', 'stt_enabled': true, 'tts_enabled': true, 'voices': [{'name': 'my-MM-NilarNeural', 'locale': 'my-MM', 'gender': 'Female'}]},
        ],
      });
}

Widget _wrap(Widget child) => ProviderScope(overrides: [apiClientProvider.overrideWithValue(_FakeApiClient())], child: MaterialApp(localizationsDelegates: const [AppStringsDelegate(), GlobalMaterialLocalizations.delegate, GlobalWidgetsLocalizations.delegate, GlobalCupertinoLocalizations.delegate], supportedLocales: const [Locale('en'), Locale('my')], home: child));

void main() {
  testWidgets('text screen renders live language selectors and a 5000-char field', (tester) async {
    await tester.pumpWidget(_wrap(const TextPage()));
    await tester.pumpAndSettle();
    expect(find.text('English · en'), findsOneWidget);
    expect(find.text('Burmese · my'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
    expect(find.textContaining('0 / 5,000'), findsOneWidget);
  });

  testWidgets('copy is disabled when translation output is empty', (tester) async {
    await tester.pumpWidget(_wrap(const TextPage()));
    await tester.pumpAndSettle();
    final copy = tester.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Copy'));
    expect(copy.onPressed, isNull);
  });

  testWidgets('unsupported camera feature is explicitly unavailable', (tester) async {
    await tester.pumpWidget(_wrap(const FeatureUnavailable(icon: Icons.camera_alt_outlined, title: 'Camera')));
    expect(find.text('Unavailable'), findsOneWidget);
    expect(find.text('Camera is not ready'), findsOneWidget);
  });

  test('Myanmar localization has readable core labels', () {
    final strings = AppStrings(const Locale('my'));
    expect(strings.translate, 'ဘာသာပြန်ရန်');
    expect(strings.providerUnavailable, isNotEmpty);
  });

  test('language model maps the FastAPI response shape', () {
    final language = Language.fromJson({'code': 'zh-Hans', 'name': 'Simplified Chinese', 'is_source_enabled': true, 'is_target_enabled': true});
    expect(language.code, 'zh-Hans');
    expect(language.isTargetEnabled, isTrue);
  });

  test('translation controller sends Auto Detect as null and handles Unicode input', () async {
    final client = _TranslationApiClient();
    final controller = TextTranslationController(client);
    controller.setSource(null);
    controller.setInput('မင်္ဂလာပါ');
    await controller.translate();
    expect(client.receivedSource, isNull);
    expect(controller.state.output, 'Hello');
    expect(controller.state.input, 'မင်္ဂလာပါ');
  });

  test('translation controller exposes a retryable API failure and swaps languages', () async {
    final controller = TextTranslationController(_TranslationApiClient(failure: const ApiFailure('RATE_LIMIT_EXCEEDED', 'Try later', statusCode: 429)));
    controller.setInput('Hello');
    controller.swap();
    expect(controller.state.source, 'my');
    expect(controller.state.target, 'en');
    await controller.translate();
    expect(controller.state.error?.code, 'RATE_LIMIT_EXCEEDED');
    expect(controller.state.output, isEmpty);
  });

  testWidgets('voice page renders selectors, recording limit, and editable transcript', (tester) async {
    await tester.pumpWidget(ProviderScope(overrides: [apiClientProvider.overrideWithValue(_VoiceApiClient())], child: MaterialApp(localizationsDelegates: const [AppStringsDelegate(), GlobalMaterialLocalizations.delegate, GlobalWidgetsLocalizations.delegate, GlobalCupertinoLocalizations.delegate], supportedLocales: const [Locale('en'), Locale('my')], home: const VoicePage())));
    await tester.pumpAndSettle();
    expect(find.text('Voice translator'), findsOneWidget);
    expect(find.text('00:00 / 00:15'), findsOneWidget);
    expect(find.text('Spoken language'), findsOneWidget);
    expect(find.text('Transcript'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
  });

  test('speech capability mapping preserves Burmese locale and voice metadata', () {
    final capabilities = SpeechCapabilities.fromJson({'provider': 'azure', 'provider_configured': true, 'speech_recognition': true, 'speech_synthesis': true, 'languages': [{'text_code': 'my', 'locale': 'my-MM', 'stt_enabled': true, 'tts_enabled': true, 'voices': [{'name': 'my-MM-NilarNeural', 'locale': 'my-MM', 'gender': 'Female'}]}]});
    expect(capabilities.languages.single.locale, 'my-MM');
    expect(capabilities.languages.single.voices.single.name, 'my-MM-NilarNeural');
  });
}

