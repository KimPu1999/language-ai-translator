import i18n from "i18next";
import { initReactI18next } from "react-i18next";

void i18n.use(initReactI18next).init({
  lng: "en",
  fallbackLng: "en",
  resources: {
    en: { translation: { appName: "Lingua", tagline: "Translation, made clear.", translate: "Translate", unavailable: "Unavailable", unavailableCopy: "This feature is planned for a future release.", noHistory: "No saved history", noFavorites: "No favorites yet", source: "Source", target: "Translation", copy: "Copy", copied: "Copied", swap: "Swap languages", characters: "characters", settings: "Settings", language: "Language", appearance: "Appearance", darkMode: "Dark mode", interface: "Interface", english: "English", myanmar: "မြန်မာ", startTranslating: "Start translating", recent: "Recent work", providerUnavailable: "Translation is not available yet", providerUnavailableCopy: "The translation engine is not configured. Your text was not saved or translated.", tryAgainLater: "Please try again later.", languagesUnavailable: "Languages could not be loaded." } },
    mm: { translation: { appName: "Lingua", tagline: "ဘာသာပြန်ခြင်းကို ရှင်းလင်းစွာ။", translate: "ဘာသာပြန်ရန်", unavailable: "မရရှိနိုင်သေးပါ", unavailableCopy: "ဤလုပ်ဆောင်ချက်ကို နောက်ထွက်ဗားရှင်းတွင် ထည့်သွင်းမည်။", noHistory: "သိမ်းထားသော မှတ်တမ်းမရှိပါ", noFavorites: "အကြိုက်ဆုံး မရှိသေးပါ", source: "မူရင်း", target: "ဘာသာပြန်", copy: "ကူးယူရန်", copied: "ကူးယူပြီး", swap: "ဘာသာစကားများ လဲရန်", characters: "စာလုံး", settings: "ဆက်တင်များ", language: "ဘာသာစကား", appearance: "အသွင်အပြင်", darkMode: "အမှောင်မုဒ်", interface: "အင်တာဖေ့စ်", english: "English", myanmar: "မြန်မာ", startTranslating: "ဘာသာပြန်ရန် စတင်ပါ", recent: "လတ်တလော", providerUnavailable: "ဘာသာပြန်စနစ် မရရှိနိုင်သေးပါ", providerUnavailableCopy: "ဘာသာပြန်စနစ်ကို မသတ်မှတ်ရသေးသောကြောင့် သင့်စာကို သိမ်းဆည်းခြင်း သို့မဟုတ် ဘာသာပြန်ခြင်း မပြုလုပ်ပါ။", tryAgainLater: "နောက်မှ ထပ်ကြိုးစားပါ။", languagesUnavailable: "ဘာသာစကားများကို ရယူ၍ မရပါ။" } },
  },
});

export default i18n;

