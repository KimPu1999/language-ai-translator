import 'package:flutter/widgets.dart';

class AppStrings {
  const AppStrings(this.locale);

  final Locale locale;

  bool get isMyanmar => locale.languageCode == 'my';
  String get appName => 'Lingua';
  String get home => isMyanmar ? 'ပင်မ' : 'Home';
  String get text => isMyanmar ? 'စာသား' : 'Text';
  String get voice => isMyanmar ? 'အသံ' : 'Voice';
  String get camera => isMyanmar ? 'ကင်မရာ' : 'Camera';
  String get documents => isMyanmar ? 'စာရွက်စာတမ်း' : 'Docs';
  String get more => isMyanmar ? 'ပိုမို' : 'More';
  String get translate => isMyanmar ? 'ဘာသာပြန်ရန်' : 'Translate';
  String get source => isMyanmar ? 'မူရင်း' : 'Source';
  String get target => isMyanmar ? 'ဘာသာပြန်' : 'Translation';
  String get swap => isMyanmar ? 'ဘာသာစကားများ လဲရန်' : 'Swap languages';
  String get copy => isMyanmar ? 'ကူးယူရန်' : 'Copy';
  String get copied => isMyanmar ? 'ကူးယူပြီး' : 'Copied';
  String get settings => isMyanmar ? 'ဆက်တင်များ' : 'Settings';
  String get unavailable => isMyanmar ? 'မရရှိနိုင်သေးပါ' : 'Unavailable';
  String get unavailableBody => isMyanmar ? 'ဤလုပ်ဆောင်ချက်ကို နောက်ထွက်ဗားရှင်းတွင် ထည့်သွင်းမည်။' : 'This feature is planned for a future release.';
  String get noHistory => isMyanmar ? 'မှတ်တမ်း မရှိသေးပါ' : 'No saved history';
  String get noFavorites => isMyanmar ? 'အကြိုက်ဆုံး မရှိသေးပါ' : 'No favorites yet';
  String get providerUnavailable => isMyanmar ? 'ဘာသာပြန်စနစ် မရရှိနိုင်သေးပါ' : 'Translation is not available yet';
  String get providerBody => isMyanmar ? 'ဘာသာပြန်စနစ်ကို မသတ်မှတ်ရသေးသောကြောင့် သင့်စာကို သိမ်းဆည်းခြင်း သို့မဟုတ် ဘာသာပြန်ခြင်း မပြုလုပ်ပါ။' : 'The translation engine is not configured. Your text was not saved or translated.';
  String get languagesError => isMyanmar ? 'ဘာသာစကားများကို ရယူ၍ မရပါ။' : 'Languages could not be loaded.';
  String get appearance => isMyanmar ? 'အသွင်အပြင်' : 'Appearance';
  String get darkMode => isMyanmar ? 'အမှောင်မုဒ်' : 'Dark mode';
  String get interfaceLanguage => isMyanmar ? 'အင်တာဖေ့စ် ဘာသာစကား' : 'Interface language';
  String get emptyOutput => isMyanmar ? 'ရလဒ်သည် ဤနေရာတွင် ပေါ်လာပါမည်' : 'Your result will appear here';
  String get loading => isMyanmar ? 'ရလဒ်ကို ပြင်ဆင်နေသည်…' : 'Preparing your result…';
  String get retry => isMyanmar ? 'ထပ်ကြိုးစားရန်' : 'Try again';
  String get comingLater => isMyanmar ? 'နောက်မှ ရရှိမည်' : 'Coming later';
}

class AppStringsDelegate extends LocalizationsDelegate<AppStrings> {
  const AppStringsDelegate();
  @override
  bool isSupported(Locale locale) => ['en', 'my'].contains(locale.languageCode);
  @override
  Future<AppStrings> load(Locale locale) async => AppStrings(locale);
  @override
  bool shouldReload(covariant LocalizationsDelegate<AppStrings> old) => false;
}

