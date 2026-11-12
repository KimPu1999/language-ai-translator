import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Copy, MessageCircle, Mic, Pause, Play, Square, Trash2, Volume2, X } from "lucide-react";
import { api } from "./api";
import { usePreferences } from "./store";
import type { Language, SpeechLanguageCapability } from "./types";

const MAX = 5000;
const MAX_SECONDS = 15;
type Speaker = "a" | "b";
type Stage = "idle" | "recording" | "transcribing" | "reviewing" | "translating" | "ready" | "playing" | "error";
type Profile = { sourceLocale: string; targetLanguage: string; voice: string; voiceLocale: string };
type Turn = { id: string; speaker: Speaker; profile: Profile; transcript: string; translation: string; stage: Stage; error?: string; blob?: Blob; audioUrl?: string };

const id = () => globalThis.crypto?.randomUUID?.() ?? `turn-${Date.now()}-${Math.random().toString(36).slice(2)}`;
const textCode = (locale: string) => ({ "en-US": "en", "my-MM": "my", "th-TH": "th", "zh-CN": "zh-Hans", "ja-JP": "ja", "ko-KR": "ko" }[locale] ?? locale);
const mime = () => typeof MediaRecorder === "undefined" ? "" : ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"].find((value) => MediaRecorder.isTypeSupported(value)) ?? "";

export default function ConversationPage() {
  const { t } = useTranslation();
  const { localLibraryOptIn, saveTranslation } = usePreferences();
  const languages = useQuery({ queryKey: ["languages"], queryFn: api.getLanguages });
  const speech = useQuery({ queryKey: ["speech-capabilities"], queryFn: api.getSpeechCapabilities });
  const [profiles, setProfiles] = useState<Record<Speaker, Profile>>({ a: { sourceLocale: "en-US", targetLanguage: "my", voice: "", voiceLocale: "my-MM" }, b: { sourceLocale: "my-MM", targetLanguage: "en", voice: "", voiceLocale: "en-US" } });
  const [turns, setTurns] = useState<Turn[]>([]);
  const [activeSpeaker, setActiveSpeaker] = useState<Speaker | null>(null);
  const [ended, setEnded] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<number | undefined>();
  const session = useRef(0);
  const turnTokens = useRef(new Map<string, number>());
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const turnsRef = useRef<Turn[]>([]);
  const cancelledRecording = useRef(false);
  const sourceCapabilities = speech.data?.languages ?? [];

  const updateTurn = (turnId: string, update: Partial<Turn>) => setTurns((items) => items.map((item) => item.id === turnId ? { ...item, ...update } : item));
  const profileFor = (speaker: Speaker) => profiles[speaker];
  const voicesFor = (speaker: Speaker) => sourceCapabilities.find((item) => item.text_code === profileFor(speaker).targetLanguage)?.voices ?? [];
  const languagesFor = useMemo(() => languages.data ?? [], [languages.data]);

  useEffect(() => { turnsRef.current = turns; }, [turns]);
  useEffect(() => () => { session.current += 1; recorder.current?.stop(); stream.current?.getTracks().forEach((track) => track.stop()); if (timer.current) window.clearInterval(timer.current); audio.current?.pause(); turnsRef.current.forEach((turn) => { if (turn.audioUrl) URL.revokeObjectURL(turn.audioUrl); }); }, []);

  const setProfile = (speaker: Speaker, update: Partial<Profile>) => setProfiles((current) => ({ ...current, [speaker]: { ...current[speaker], ...update } }));

  const start = async (speaker: Speaker) => {
    if (ended || activeSpeaker || playingId || !speech.data?.speech_recognition) return;
    const format = mime();
    if (!format) { setTurns((items) => [...items, { id: id(), speaker, profile: profileFor(speaker), transcript: "", translation: "", stage: "error", error: t("conversationRecordingUnsupported") }]); return; }
    try {
      const input = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = input; chunks.current = []; cancelledRecording.current = false;
      const current = new MediaRecorder(input, { mimeType: format });
      recorder.current = current; setActiveSpeaker(speaker); setElapsed(0);
      current.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data); };
      current.onstop = () => { const blob = new Blob(chunks.current, { type: format }); void finish(speaker, blob); };
      current.start();
      timer.current = window.setInterval(() => setElapsed((value) => { if (value + 1 >= MAX_SECONDS) { current.stop(); } return Math.min(value + 1, MAX_SECONDS); }), 1000);
    } catch { setTurns((items) => [...items, { id: id(), speaker, profile: profileFor(speaker), transcript: "", translation: "", stage: "error", error: t("conversationPermissionDenied") }]); }
  };

  const finish = async (speaker: Speaker, blob: Blob) => {
    if (timer.current) window.clearInterval(timer.current); timer.current = undefined;
    stream.current?.getTracks().forEach((track) => track.stop()); stream.current = null; recorder.current = null; setActiveSpeaker(null);
    if (cancelledRecording.current || !blob.size) return;
    const turnId = id(); const token = session.current; turnTokens.current.set(turnId, token);
    const turn: Turn = { id: turnId, speaker, profile: profileFor(speaker), transcript: "", translation: "", stage: "transcribing", blob };
    setTurns((items) => [...items, turn]);
    try { const result = await api.transcribeVoice(blob, turn.profile.sourceLocale); if (session.current !== token || turnTokens.current.get(turnId) !== token) return; updateTurn(turnId, { transcript: result.transcript.slice(0, MAX), stage: "reviewing" }); }
    catch (error) { if (session.current === token) updateTurn(turnId, { stage: "error", error: (error as Error).message }); }
  };
  const stop = () => { if (recorder.current?.state === "recording") recorder.current.stop(); };
  const cancel = () => { cancelledRecording.current = true; session.current += 1; recorder.current?.stop(); stream.current?.getTracks().forEach((track) => track.stop()); setActiveSpeaker(null); setElapsed(0); };

  const translate = async (turn: Turn) => {
    if (!turn.transcript.trim() || turn.stage === "translating" || ended) return;
    const token = session.current; turnTokens.current.set(turn.id, token); updateTurn(turn.id, { stage: "translating", error: undefined, translation: "" });
    try { const result = await api.translateText({ source_language: textCode(turn.profile.sourceLocale), target_language: turn.profile.targetLanguage, text: turn.transcript }); if (session.current !== token || turnTokens.current.get(turn.id) !== token) return; updateTurn(turn.id, { translation: result.translated_text, stage: "ready" }); }
    catch (error) { if (session.current === token) updateTurn(turn.id, { stage: "error", error: (error as Error).message }); }
  };
  const synthesize = async (turn: Turn) => {
    if (!turn.translation || !turn.profile.voice || playingId) return;
    const token = session.current; updateTurn(turn.id, { stage: "translating", error: undefined });
    try { const blob = await api.synthesizeVoice({ text: turn.translation, locale: turn.profile.voiceLocale, voice: turn.profile.voice }); if (session.current !== token) return; const url = URL.createObjectURL(blob); if (turn.audioUrl) URL.revokeObjectURL(turn.audioUrl); updateTurn(turn.id, { audioUrl: url, stage: "ready" }); play(turn.id, url); }
    catch (error) { if (session.current === token) updateTurn(turn.id, { stage: "error", error: (error as Error).message }); }
  };
  const play = (turnId: string, url?: string) => { const source = url ?? turns.find((turn) => turn.id === turnId)?.audioUrl; if (!source) return; audio.current?.pause(); const player = new Audio(source); audio.current = player; setPlayingId(turnId); updateTurn(turnId, { stage: "playing" }); player.onended = () => { setPlayingId(null); updateTurn(turnId, { stage: "ready" }); }; void player.play().catch(() => { setPlayingId(null); updateTurn(turnId, { stage: "error", error: t("conversationPlaybackFailed") }); }); };
  const pause = () => { audio.current?.pause(); if (playingId) updateTurn(playingId, { stage: "ready" }); setPlayingId(null); };
  const clear = () => { session.current += 1; recorder.current?.stop(); stream.current?.getTracks().forEach((track) => track.stop()); audio.current?.pause(); turns.forEach((turn) => { if (turn.audioUrl) URL.revokeObjectURL(turn.audioUrl); }); setTurns([]); setEnded(false); setActiveSpeaker(null); setPlayingId(null); };
  const end = () => { cancel(); audio.current?.pause(); setPlayingId(null); setEnded(true); };
  const save = (turn: Turn) => { if (!localLibraryOptIn || !turn.translation) return; saveTranslation({ id: turn.id, sourceLanguage: textCode(turn.profile.sourceLocale), targetLanguage: turn.profile.targetLanguage, sourceText: turn.transcript, translatedText: turn.translation, createdAt: new Date().toISOString() }); };

  return <div className="mx-auto max-w-6xl"><div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="mb-3 text-xs font-bold uppercase tracking-[.18em] text-blue-600">CONVERSATION</p><h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("conversationTitle")}</h1><p className="subtle mt-2 max-w-2xl text-sm leading-6">{t("conversationCopy")}</p></div><div className="flex gap-2"><button onClick={end} disabled={ended} className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-bold disabled:opacity-40 dark:border-slate-700">{t("conversationEnd")}</button><button onClick={clear} className="inline-flex items-center gap-2 rounded-xl bg-navy px-3 py-2 text-xs font-bold text-white"><Trash2 size={14} />{t("conversationClear")}</button></div></div>
    <div className="mb-5 rounded-2xl border border-blue-100 bg-blue-50/70 p-4 text-sm text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/20 dark:text-blue-100"><MessageCircle className="mr-2 inline" size={16} />{t("conversationPushToTalk")}</div>
    <div className="grid gap-4 lg:grid-cols-2">{(["a", "b"] as Speaker[]).map((speaker) => <SpeakerCard key={speaker} speaker={speaker} profile={profileFor(speaker)} languages={languagesFor} capability={sourceCapabilities} voices={voicesFor(speaker)} active={activeSpeaker === speaker} blocked={Boolean(activeSpeaker && activeSpeaker !== speaker) || Boolean(playingId) || ended} elapsed={elapsed} onProfile={(update) => setProfile(speaker, update)} onStart={() => void start(speaker)} onStop={stop} onCancel={cancel} t={t} />)}</div>
    <div className="mt-6 space-y-4">{turns.map((turn) => <TurnCard key={turn.id} turn={turn} language={languagesFor} playing={playingId === turn.id} onChange={(transcript) => updateTurn(turn.id, { transcript: transcript.slice(0, MAX), translation: "", stage: "reviewing" })} onTranslate={() => void translate(turn)} onSynthesize={() => void synthesize(turn)} onPlay={() => play(turn.id)} onPause={pause} onSave={() => save(turn)} localLibraryOptIn={localLibraryOptIn} t={t} />)}</div>
    {ended && <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 text-center text-sm font-semibold dark:border-slate-700 dark:bg-[#13233b]">{t("conversationEnded")}</div>}
  </div>;
}

function SpeakerCard({ speaker, profile, languages, capability, voices, active, blocked, elapsed, onProfile, onStart, onStop, onCancel, t }: { speaker: Speaker; profile: Profile; languages: Language[]; capability: SpeechLanguageCapability[]; voices: { name: string; locale: string }[]; active: boolean; blocked: boolean; elapsed: number; onProfile: (update: Partial<Profile>) => void; onStart: () => void; onStop: () => void; onCancel: () => void; t: (key: string) => string }) {
  return <section className="surface rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-[#13233b]"><div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-extrabold">{speaker === "a" ? t("conversationPersonA") : t("conversationPersonB")}</h2><span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${active ? "bg-rose-100 text-rose-700" : "bg-slate-100 text-slate-500 dark:bg-slate-800"}`}>{active ? t("conversationRecording") : t("conversationReady")}</span></div><div className="grid gap-3 sm:grid-cols-2"><label><span className="field-label">{t("spokenLanguage")}</span><select value={profile.sourceLocale} onChange={(event) => onProfile({ sourceLocale: event.target.value })} className="voice-select w-full">{capability.filter((item) => item.stt_enabled).map((item) => <option key={item.locale} value={item.locale}>{languages.find((language) => language.code === item.text_code)?.name ?? item.text_code} · {item.locale}</option>)}</select></label><label><span className="field-label">{t("translateInto")}</span><select value={profile.targetLanguage} onChange={(event) => { const target = capability.find((item) => item.text_code === event.target.value); onProfile({ targetLanguage: event.target.value, voice: "", voiceLocale: target?.locale ?? profile.voiceLocale }); }} className="voice-select w-full">{languages.filter((language) => language.is_target_enabled).map((item) => <option key={item.code} value={item.code}>{item.name} · {item.code}</option>)}</select></label></div><label className="mt-3 block"><span className="field-label">{t("voice")}</span><select value={profile.voice} onChange={(event) => { const voice = voices.find((item) => item.name === event.target.value); onProfile({ voice: event.target.value, voiceLocale: voice?.locale ?? profile.voiceLocale }); }} className="voice-select w-full" disabled={!voices.length}><option value="">{voices.length ? t("voice") : t("noVoicesAvailable")}</option>{voices.map((voice) => <option key={voice.name} value={voice.name}>{voice.name} · {voice.locale}</option>)}</select></label><div className="mt-4 flex flex-wrap items-center gap-2"><button onClick={active ? onStop : onStart} disabled={blocked && !active} className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-40 ${active ? "bg-rose-500" : "bg-navy"}`}>{active ? <Square size={15} fill="currentColor" /> : <Mic size={15} />}{active ? t("conversationStop") : t("conversationPush")}</button>{active && <><span className="text-xs font-bold tabular-nums text-rose-600">00:{String(elapsed).padStart(2, "0")} / 00:15</span><button onClick={onCancel} className="inline-flex items-center gap-1 rounded-lg px-2 py-2 text-xs font-bold text-slate-500"><X size={14} />{t("cancel")}</button></>}</div></section>;
}

function TurnCard({ turn, language, playing, onChange, onTranslate, onSynthesize, onPlay, onPause, onSave, localLibraryOptIn, t }: { turn: Turn; language: Language[]; playing: boolean; onChange: (value: string) => void; onTranslate: () => void; onSynthesize: () => void; onPlay: () => void; onPause: () => void; onSave: () => void; localLibraryOptIn: boolean; t: (key: string) => string }) {
  return <article className={`rounded-3xl border p-5 ${turn.speaker === "a" ? "border-blue-100 bg-blue-50/50 dark:border-blue-900/50 dark:bg-blue-950/20" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-[#13233b]"}`}><div className="mb-3 flex items-center justify-between"><span className="text-xs font-bold uppercase tracking-wider text-slate-400">{turn.speaker === "a" ? t("conversationPersonA") : t("conversationPersonB")} · {turn.stage}</span>{turn.translation && <span className="text-xs font-semibold text-blue-600">{language.find((item) => item.code === turn.profile.targetLanguage)?.name ?? turn.profile.targetLanguage}</span>}</div><textarea aria-label={`${t("conversationTranscript")} ${turn.speaker}`} value={turn.transcript} onChange={(event) => onChange(event.target.value)} maxLength={MAX} disabled={turn.stage === "transcribing" || turn.stage === "translating"} className="min-h-24 w-full resize-y rounded-xl border border-slate-200 bg-white/80 p-3 text-sm leading-6 outline-none focus:border-blue-400 dark:border-slate-700 dark:bg-[#101d31] dark:text-white" /><div className="mt-2 flex flex-wrap items-center justify-between gap-2"><span className="text-xs text-slate-400">{turn.transcript.length} / {MAX}</span><div className="flex flex-wrap gap-2"><button onClick={onTranslate} disabled={!turn.transcript.trim() || turn.stage === "transcribing" || turn.stage === "translating"} className="rounded-lg bg-navy px-3 py-2 text-xs font-bold text-white disabled:opacity-40">{turn.stage === "translating" ? t("translating") : t("translate")}</button><button onClick={() => { void navigator.clipboard?.writeText(turn.transcript); }} disabled={!turn.transcript} className="inline-flex items-center gap-1 rounded-lg px-2 py-2 text-xs font-bold text-slate-500 disabled:opacity-40"><Copy size={14} />{t("copy")}</button></div></div>{turn.translation && <div className="mt-4 rounded-2xl border border-blue-100 bg-white/70 p-4 dark:border-slate-700 dark:bg-[#101d31]"><p className="whitespace-pre-wrap text-sm leading-6 dark:text-white">{turn.translation}</p><div className="mt-3 flex flex-wrap gap-2"><button onClick={onSynthesize} disabled={!turn.profile.voice || Boolean(playing)} className="inline-flex items-center gap-1 rounded-lg border border-blue-200 px-3 py-2 text-xs font-bold text-blue-700 disabled:opacity-40"><Volume2 size={14} />{t("conversationSynthesize")}</button>{turn.audioUrl && <button onClick={playing ? onPause : onPlay} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold dark:border-slate-700">{playing ? <Pause size={14} /> : <Play size={14} />}{playing ? t("pause") : t("conversationReplay")}</button>}{localLibraryOptIn && <button onClick={onSave} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold dark:border-slate-700">{t("saveLocally")}</button>}</div></div>}{turn.error && <p role="alert" className="mt-3 text-sm font-semibold text-amber-700 dark:text-amber-200">{turn.error}</p>}</article>;
}
