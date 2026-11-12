import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:lingua_mobile/core/localization/app_strings.dart';
import 'package:lingua_mobile/core/models/language.dart';
import 'package:lingua_mobile/core/network/api_client.dart';
import 'package:lingua_mobile/core/providers/app_providers.dart';
import 'package:lingua_mobile/features/text/text_page.dart';
import 'package:lingua_mobile/widgets/feature_unavailable.dart';

class _FakeApiClient extends ApiClient {
  @override
  Future<List<Map<String, dynamic>>> getLanguages() async => [
        {'code': 'en', 'name': 'English', 'is_source_enabled': true, 'is_target_enabled': true},
        {'code': 'my', 'name': 'Burmese', 'is_source_enabled': true, 'is_target_enabled': true},
      ];

  @override
  Future<Map<String, dynamic>> getCapabilities() async => {'text_translation': false, 'provider_configured': false, 'supported_operations': ['text_translation']};
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
}

