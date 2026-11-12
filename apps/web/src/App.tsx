import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowLeftRight,
  Camera,
  Check,
  ChevronDown,
  Clipboard,
  Copy,
  FileText,
  Heart,
  History,
  Home,
  Languages,
  Menu,
  MessageCircle,
  Mic,
  Moon,
  RotateCcw,
  Save,
  Send,
  Settings as SettingsIcon,
  Sparkles,
  Sun,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api } from "./api";
import i18n from "./i18n";
import { usePreferences } from "./store";
import type { Language } from "./types";
import VoicePage from "./VoicePage";
import ConversationPage from "./ConversationPage";
import CameraPage from "./CameraPage";
import DocumentPage from "./DocumentPage";

const MAX_CHARACTERS = 5000;
const navItems: { to: string; label: string; icon: LucideIcon }[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/translate", label: "Text Translator", icon: Languages },
  { to: "/voice", label: "Voice", icon: Mic },
  { to: "/conversation", label: "Conversation", icon: MessageCircle },
  { to: "/camera", label: "Camera", icon: Camera },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/history", label: "History", icon: History },
  { to: "/favorites", label: "Favorites", icon: Heart },
];

function App() {
  const { theme, toggleTheme, uiLanguage, setUiLanguage } = usePreferences();
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => { document.documentElement.classList.toggle("dark", theme === "dark"); }, [theme]);
  useEffect(() => { void i18n.changeLanguage(uiLanguage); }, [uiLanguage]);
  return (
    <div className="min-h-screen bg-mist transition-colors dark:bg-[#0d1728]">
      <Header onMenu={() => setMobileOpen(true)} theme={theme} toggleTheme={toggleTheme} uiLanguage={uiLanguage} setUiLanguage={setUiLanguage} />
      <div className="mx-auto flex max-w-[1440px]">
        <Sidebar />
        <main className="min-w-0 flex-1 px-4 pb-24 pt-6 sm:px-8 lg:px-12 lg:pb-12 lg:pt-10">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/translate" element={<TranslatorPage />} />
            <Route path="/voice" element={<VoicePage />} />
            <Route path="/conversation" element={<ConversationPage />} />
            <Route path="/camera" element={<CameraPage />} />
            <Route path="/documents" element={<DocumentPage />} />
            <Route path="/history" element={<CollectionPage type="history" />} />
            <Route path="/favorites" element={<CollectionPage type="favorites" />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
      <MobileNav />
      {mobileOpen && <MobileMenu close={() => setMobileOpen(false)} />}
    </div>
  );
}

function Header({ onMenu, theme, toggleTheme, uiLanguage, setUiLanguage }: { onMenu: () => void; theme: "light" | "dark"; toggleTheme: () => void; uiLanguage: "en" | "mm"; setUiLanguage: (language: "en" | "mm") => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const nextLanguage = uiLanguage === "en" ? "mm" : "en";
  return <header className="surface sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur dark:bg-[#101d31]/90">
    <div className="mx-auto flex h-[72px] max-w-[1440px] items-center justify-between px-4 sm:px-8 lg:px-12">
      <div className="flex items-center gap-3"><button aria-label="Open navigation" className="rounded-xl p-2 lg:hidden" onClick={onMenu}><Menu size={21} /></button><button className="flex items-center gap-2" onClick={() => navigate("/")}><span className="grid h-9 w-9 place-items-center rounded-xl bg-navy text-white shadow-lg shadow-blue-900/15"><Sparkles size={18} /></span><span className="text-lg font-extrabold tracking-tight">{t("appName")}</span></button></div>
      <div className="flex items-center gap-1"><button aria-label="Toggle dark mode" className="rounded-xl p-2.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={toggleTheme}>{theme === "light" ? <Moon size={18} /> : <Sun size={18} />}</button><button aria-label="Switch interface language" className="rounded-xl px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" onClick={() => { setUiLanguage(nextLanguage); void i18n.changeLanguage(nextLanguage); }}>{uiLanguage === "en" ? "EN" : "MM"}</button><button className="rounded-xl p-2.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Settings" onClick={() => navigate("/settings")}><SettingsIcon size={19} /></button><div className="hidden h-8 w-8 place-items-center rounded-full bg-sky font-bold text-navy sm:grid">L</div></div>
    </div>
  </header>;
}

function Sidebar() { return <aside className="hidden w-64 shrink-0 px-5 pb-8 pt-8 lg:block"><nav aria-label="Main navigation" className="space-y-1">{navItems.map(({ to, label, icon: Icon }) => <NavItem key={to} to={to} label={label} Icon={Icon} />)}</nav><div className="mt-10 rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 to-white p-4 dark:border-slate-700 dark:from-[#18345e] dark:to-[#13233b]"><Sparkles className="mb-3 text-blue-500" size={19} /><p className="text-sm font-bold">Your calm translation space</p><p className="subtle mt-1 text-xs leading-5">Private by design. Local saving is always opt-in.</p></div></aside>; }
function NavItem({ to, label, Icon }: { to: string; label: string; Icon: LucideIcon }) { return <NavLink to={to} className={({ isActive }) => `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${isActive ? "bg-navy text-white shadow-md shadow-blue-900/15" : "text-slate-500 hover:bg-white hover:text-navy dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"}`}><Icon size={18} /><span>{label}</span></NavLink>; }
function MobileNav() { return <nav aria-label="Mobile navigation" className="surface fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-slate-200 bg-white/95 px-2 py-2 backdrop-blur lg:hidden dark:bg-[#101d31]/95">{navItems.slice(0, 4).map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => `grid place-items-center gap-1 rounded-xl py-1 text-[10px] font-semibold ${isActive ? "text-blue-600" : "text-slate-400"}`}><Icon size={18} /><span>{label === "Text Translator" ? "Translate" : label}</span></NavLink>)}</nav>; }
function MobileMenu({ close }: { close: () => void }) { return <div className="fixed inset-0 z-40 bg-navy/25 lg:hidden" onClick={close}><aside className="surface h-full w-[min(84vw,320px)] bg-white p-5 shadow-2xl dark:bg-[#13233b]" onClick={(event) => event.stopPropagation()}><div className="mb-8 flex items-center justify-between"><span className="font-extrabold">Menu</span><button aria-label="Close navigation" onClick={close}><X size={20} /></button></div><nav className="space-y-1">{navItems.map(({ to, label, icon: Icon }) => <NavItem key={to} to={to} label={label} Icon={Icon} />)}<NavItem to="/settings" label="Settings" Icon={SettingsIcon} /></nav></aside></div>; }

function HomePage() { const { t } = useTranslation(); const navigate = useNavigate(); return <div className="mx-auto max-w-5xl"><section className="relative overflow-hidden rounded-[28px] bg-navy px-6 py-10 text-white shadow-soft sm:px-10 sm:py-14"><div className="relative z-10 max-w-xl"><span className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-semibold text-blue-100"><Sparkles size={14} /> Clear words, anywhere</span><h1 className="text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">{t("tagline")}</h1><p className="mt-5 max-w-md text-sm leading-6 text-blue-100 sm:text-base">A focused workspace for moving between languages with clarity, care, and no invented answers.</p><button className="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-navy shadow-lg transition hover:-translate-y-0.5" onClick={() => navigate("/translate")}>{t("startTranslating")} <ArrowLeftRight size={17} /></button></div><div className="absolute -right-20 -top-24 h-80 w-80 rounded-full bg-blue-400/20 blur-3xl" /></section><section className="mt-8 grid gap-4 sm:grid-cols-3"><FeatureCard icon={Languages} title="Text" copy="Write and translate with a clear, calm editor." onClick={() => navigate("/translate")} /><FeatureCard icon={Mic} title="Voice" copy="Record, review, translate, and listen back." onClick={() => navigate("/voice")} /><FeatureCard icon={Camera} title="Camera" copy="Image translation is coming in a future phase." onClick={() => navigate("/camera")} /></section></div>; }
function FeatureCard({ icon: Icon, title, copy, onClick }: { icon: LucideIcon; title: string; copy: string; onClick: () => void }) { return <button onClick={onClick} className="surface group rounded-2xl border border-slate-200 bg-white p-5 text-left transition hover:-translate-y-0.5 hover:shadow-soft dark:border-slate-700"><span className="mb-7 grid h-10 w-10 place-items-center rounded-xl bg-sky text-blue-600"><Icon size={19} /></span><p className="font-bold">{title}</p><p className="subtle mt-1 text-sm leading-5">{copy}</p><span className="mt-5 block text-xs font-bold text-blue-600 opacity-0 transition group-hover:opacity-100">Open →</span></button>; }

function useLanguageData() { const languages = useQuery({ queryKey: ["languages"], queryFn: api.getLanguages }); const capabilities = useQuery({ queryKey: ["capabilities"], queryFn: api.getCapabilities }); return { languages, capabilities }; }

function TranslatorPage() {
  const { t } = useTranslation();
  const { languages, capabilities } = useLanguageData();
  const { localLibraryOptIn, saveTranslation, toggleFavorite, favorites } = usePreferences();
  const [source, setSource] = useState("en");
  const [target, setTarget] = useState("my");
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [copied, setCopied] = useState(false);
  const [lastPayload, setLastPayload] = useState<{ source_language: string | null; target_language: string; text: string } | null>(null);
  const mutation = useMutation({ mutationFn: api.translateText, onSuccess: (response) => { setResult(response.translated_text); setCopied(false); }, onError: () => setResult("") });
  const list = languages.data ?? [];
  const sourceLanguage = list.find((language) => language.code === source);
  const targetLanguage = list.find((language) => language.code === target);
  const busy = mutation.isPending;
  const canTranslate = text.length > 0 && text.length <= MAX_CHARACTERS && target !== "auto" && source !== target && !busy;
  const clear = () => { setText(""); setResult(""); setLastPayload(null); setCopied(false); mutation.reset(); };
  const selectLanguage = (setter: (value: string) => void, value: string) => { setter(value); setResult(""); setCopied(false); mutation.reset(); };
  const swap = () => { if (source === "auto") return; const oldSource = source; setSource(target); setTarget(oldSource); setResult(""); setCopied(false); mutation.reset(); };
  const submit = () => { if (!canTranslate) return; const payload = { source_language: source === "auto" ? null : source, target_language: target, text }; setLastPayload(payload); setResult(""); setCopied(false); mutation.mutate(payload); };
  const savedId = lastPayload && result ? `${lastPayload.source_language ?? "auto"}-${lastPayload.target_language}-${lastPayload.text}` : "";
  const savedTranslation = lastPayload && result ? { id: savedId, sourceLanguage: lastPayload.source_language ?? "auto", targetLanguage: lastPayload.target_language, sourceText: lastPayload.text, translatedText: result, createdAt: new Date().toISOString() } : null;
  const isFavorite = savedTranslation ? favorites.some((item) => item.id === savedTranslation.id) : false;
  return <div className="mx-auto max-w-6xl"><PageIntro eyebrow="TRANSLATE" title={t("translate")} copy="Move from thought to meaning with a focused, editable workspace." /><div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end"><LanguageSelect label={t("source")} value={source} languages={list} autoDetect onChange={(value) => selectLanguage(setSource, value)} /><button aria-label={t("swap")} title={t("swap")} onClick={swap} disabled={source === "auto"} className="grid h-11 w-11 shrink-0 place-items-center self-center rounded-xl border border-slate-200 bg-white text-slate-500 transition hover:border-blue-300 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:bg-[#13233b]"><ArrowLeftRight size={18} /></button><LanguageSelect label={t("target")} value={target} languages={list} onChange={(value) => selectLanguage(setTarget, value)} /></div>{languages.isLoading && <Notice title={t("loadingLanguages")} copy="Loading the supported language list from the API…" tone="info" />}{languages.isError && <Notice title={t("languagesUnavailable")} copy="Check that the API is running and your VITE_API_BASE_URL is correct." tone="warning" />}{capabilities.data && !capabilities.data.provider_configured && <Notice title={t("providerNotConfigured")} copy={t("providerUnavailableCopy")} tone="warning" />}<div className="grid gap-4 lg:grid-cols-2"><EditorCard label={`${sourceLanguage?.name ?? (source === "auto" ? t("autoDetect") : source)} · ${t("source")}`}><textarea aria-label={t("source")} value={text} onChange={(event) => { setText(event.target.value.slice(0, MAX_CHARACTERS)); setResult(""); setCopied(false); mutation.reset(); }} placeholder={t("inputPlaceholder")} className="min-h-[260px] w-full resize-none bg-transparent text-base leading-7 text-ink outline-none placeholder:text-slate-300 dark:text-white dark:placeholder:text-slate-600" /><div className="mt-4 flex flex-col gap-3 border-t border-slate-100 pt-3 sm:flex-row sm:items-center sm:justify-between dark:border-slate-700"><div className="flex items-center justify-between gap-3"><span className={`text-xs ${text.length >= MAX_CHARACTERS ? "font-bold text-amber-600" : "subtle"}`}>{text.length.toLocaleString()} / {MAX_CHARACTERS.toLocaleString()} {t("characters")}</span>{text && <button aria-label={t("clear")} onClick={clear} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><X size={13} />{t("clear")}</button>}</div><button disabled={!canTranslate} onClick={submit} className="inline-flex items-center justify-center gap-2 rounded-xl bg-navy px-4 py-2.5 text-sm font-bold text-white transition hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-40"><Send size={15} />{busy ? t("translating") : t("translate")}</button></div></EditorCard><EditorCard label={`${targetLanguage?.name ?? target} · ${t("target")}`} output><div aria-live="polite" className="flex min-h-[260px] flex-col">{busy ? <LoadingState /> : result ? <><p className="whitespace-pre-wrap text-base leading-7 text-ink dark:text-white">{result}</p><div className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 dark:border-slate-700"><span className="subtle text-xs">{t("providerResult")}</span><div className="flex items-center gap-1"><button className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold text-slate-500 hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800" onClick={() => { void navigator.clipboard?.writeText(result); setCopied(true); }} disabled={!result}>{copied ? <Check size={14} /> : <Clipboard size={14} />}{copied ? t("copied") : t("copy")}</button>{localLibraryOptIn && savedTranslation && <><button className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => saveTranslation(savedTranslation)}><Save size={14} />{t("saveLocally")}</button><button aria-label={t("favorite")} className={`rounded-lg p-2 ${isFavorite ? "text-rose-500" : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"}`} onClick={() => toggleFavorite(savedTranslation)}><Heart size={15} fill={isFavorite ? "currentColor" : "none"} /></button></>}</div></div></> : mutation.isError ? <ErrorState error={mutation.error as Error} onRetry={() => { if (lastPayload) mutation.mutate(lastPayload); }} /> : <EmptyOutput />}</div></EditorCard></div></div>;
}

function PageIntro({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) { return <div className="mb-8"><p className="mb-3 text-xs font-bold uppercase tracking-[.18em] text-blue-600">{eyebrow}</p><h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1><p className="subtle mt-2 max-w-xl text-sm leading-6 sm:text-base">{copy}</p></div>; }
function LanguageSelect({ label, value, languages, onChange, autoDetect = false }: { label: string; value: string; languages: Language[]; onChange: (value: string) => void; autoDetect?: boolean }) { return <label className="relative min-w-0 flex-1"><span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</span><select value={value} onChange={(event) => onChange(event.target.value)} className="surface w-full appearance-none rounded-xl border border-slate-200 bg-white px-3 py-3 pr-9 text-sm font-semibold text-ink shadow-sm outline-none dark:border-slate-700 dark:bg-[#13233b] dark:text-white">{autoDetect && <option value="auto">Auto Detect</option>}{languages.length ? languages.map((language) => <option key={language.code} value={language.code}>{language.name} · {language.code}</option>) : <option value={value}>{value}</option>}</select><ChevronDown className="pointer-events-none absolute bottom-3 right-3 text-slate-400" size={16} /></label>; }
function EditorCard({ label, children, output = false }: { label: string; children: ReactNode; output?: boolean }) { return <section className={`surface rounded-2xl border ${output ? "border-blue-100" : "border-slate-200"} bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-[#13233b]`}><div className="mb-5 flex items-center justify-between"><span className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</span>{output && <Copy size={17} className="text-slate-300" />}</div>{children}</section>; }
function EmptyOutput() { const { t } = useTranslation(); return <div className="flex flex-1 flex-col items-center justify-center text-center"><div><div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-sky text-blue-500"><Sparkles size={20} /></div><p className="text-sm font-semibold text-slate-400">{t("target")} will appear here</p><p className="subtle mt-1 text-xs">{t("resultHint")}</p></div><button disabled className="mt-6 inline-flex cursor-not-allowed items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold text-slate-300 dark:text-slate-600"><Clipboard size={14} />{t("copy")}</button></div>; }
function LoadingState() { const { t } = useTranslation(); return <div className="grid flex-1 place-items-center"><div className="text-center"><div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-blue-100 border-t-blue-600" /><p className="subtle text-sm">{t("translating")}</p></div></div>; }
function ErrorState({ error, onRetry }: { error: Error; onRetry: () => void }) { const { t } = useTranslation(); return <div role="alert" className="flex flex-1 items-center"><div className="w-full rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/50 dark:bg-amber-950/30"><p className="text-sm font-bold text-amber-900 dark:text-amber-100">{t("providerUnavailable")}</p><p className="mt-1 text-sm leading-6 text-amber-800 dark:text-amber-200">{error.message}. {t("noInventedResult")}</p><button onClick={onRetry} className="mt-3 inline-flex items-center gap-2 rounded-lg bg-amber-900 px-3 py-2 text-xs font-bold text-white hover:bg-amber-800"><RotateCcw size={13} />{t("retry")}</button></div></div>; }
function Notice({ title, copy, tone }: { title: string; copy: string; tone: "warning" | "info" }) { return <div className={`mb-5 rounded-2xl border p-4 ${tone === "warning" ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100" : "border-blue-100 bg-blue-50 text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100"}`}><p className="text-sm font-bold">{title}</p><p className="mt-1 text-sm">{copy}</p></div>; }

function CollectionPage({ type }: { type: "history" | "favorites" }) { const { t } = useTranslation(); const { localLibraryOptIn, history, favorites } = usePreferences(); const items = type === "history" ? history : favorites; const title = type === "history" ? t("history") : t("favorites"); return <div className="mx-auto max-w-4xl"><PageIntro eyebrow={title.toUpperCase()} title={title} copy={t("localLibraryCopy")} />{!localLibraryOptIn ? <div className="surface grid min-h-[360px] place-items-center rounded-3xl border border-slate-200 bg-white p-8 text-center dark:border-slate-700 dark:bg-[#13233b]"><div><div className="mx-auto mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-sky text-blue-600"><History size={27} /></div><h2 className="text-xl font-bold">{t("localSavingOff")}</h2><p className="subtle mx-auto mt-2 max-w-md text-sm leading-6">{t("localSavingOffCopy")}</p></div></div> : items.length === 0 ? <div className="surface grid min-h-[360px] place-items-center rounded-3xl border border-slate-200 bg-white p-8 text-center dark:border-slate-700 dark:bg-[#13233b]"><div><Heart className="mx-auto mb-5 text-blue-500" size={30} /><h2 className="text-xl font-bold">{type === "history" ? t("noHistory") : t("noFavorites")}</h2></div></div> : <div className="space-y-3">{items.map((item) => <article key={item.id} className="surface rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-[#13233b]"><div className="mb-3 flex justify-between text-xs font-bold uppercase tracking-wider text-slate-400"><span>{item.sourceLanguage} → {item.targetLanguage}</span><span>{new Date(item.createdAt).toLocaleDateString()}</span></div><p className="text-sm text-slate-500">{item.sourceText}</p><p className="mt-3 font-semibold">{item.translatedText}</p></article>)}</div>}</div>; }

function SettingsPage() { const { t, i18n } = useTranslation(); const { theme, toggleTheme, uiLanguage, setUiLanguage, localLibraryOptIn, setLocalLibraryOptIn } = usePreferences(); return <div className="mx-auto max-w-3xl"><PageIntro eyebrow="PREFERENCES" title={t("settings")} copy="Make Lingua feel like yours. These preferences are stored locally in this browser." /><div className="surface divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white dark:divide-slate-700 dark:border-slate-700 dark:bg-[#13233b]"><SettingRow title={t("appearance")} copy={t("darkMode")}><button aria-label="Toggle dark mode" onClick={toggleTheme} className={`relative h-7 w-12 rounded-full p-1 transition ${theme === "dark" ? "bg-blue-600" : "bg-slate-200"}`}><span className={`block h-5 w-5 rounded-full bg-white shadow transition ${theme === "dark" ? "translate-x-5" : ""}`} /></button></SettingRow><SettingRow title={t("interface")} copy={t("language")}><select value={uiLanguage} onChange={(event) => { const next = event.target.value as "en" | "mm"; setUiLanguage(next); void i18n.changeLanguage(next); }} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-[#101d31]"><option value="en">{t("english")}</option><option value="mm">{t("myanmar")}</option></select></SettingRow><SettingRow title={t("localSaving")} copy={t("localSavingSettingCopy")}><button role="switch" aria-checked={localLibraryOptIn} aria-label={t("localSaving")} onClick={() => setLocalLibraryOptIn(!localLibraryOptIn)} className={`relative h-7 w-12 rounded-full p-1 transition ${localLibraryOptIn ? "bg-blue-600" : "bg-slate-200"}`}><span className={`block h-5 w-5 rounded-full bg-white shadow transition ${localLibraryOptIn ? "translate-x-5" : ""}`} /></button></SettingRow></div></div>; }
function SettingRow({ title, copy, children }: { title: string; copy: string; children: ReactNode }) { return <div className="flex items-center justify-between gap-4 p-5"><div><p className="font-bold">{title}</p><p className="subtle mt-1 text-sm">{copy}</p></div>{children}</div>; }

export default App;
