import { useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertCircle,
  Check,
  CircleStop,
  Copy,
  Mic,
  Pause,
  Play,
  RotateCcw,
  Square,
  Trash2,
  Volume2,
  X,
} from "lucide-react";
import { api } from "./api";
import type { Language, SpeechLanguageCapability } from "./types";

const MAX_RECORDING_SECONDS = 15;
const MAX_CHARACTERS = 5000;

type RequestPayload = { blob: Blob; locale: string; requestId: number };
type TranslationPayload = { text: string; requestId: number };
type SynthesisPayload = { requestId: number };

export default function VoicePage() {
  const { t } = useTranslation();
  const languages = useQuery({ queryKey: ["languages"], queryFn: api.getLanguages });
  const capabilities = useQuery({ queryKey: ["speech-capabilities"], queryFn: api.getSpeechCapabilities });
  const [sourceLocale, setSourceLocale] = useState("en-US");
  const [targetLanguage, setTargetLanguage] = useState("my");
  const [voiceName, setVoiceName] = useState("");
  const [transcript, setTranscript] = useState("");
  const [translation, setTranslation] = useState("");
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [recordError, setRecordError] = useState("");
  const [copied, setCopied] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasAudio, setHasAudio] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const startedAtRef = useRef(0);
  const cancelledRef = useRef(false);
  const disposedRef = useRef(false);
  const requestIdRef = useRef(0);
  const translationRequestIdRef = useRef(0);
  const synthesisRequestIdRef = useRef(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const speechLanguages = capabilities.data?.languages ?? [];
  const sourceOptions = speechLanguages.filter((item) => item.stt_enabled);
  const targetOptions = languages.data?.filter((item) => item.is_target_enabled) ?? [];
  const sourceCapability = speechLanguages.find((item) => item.locale === sourceLocale);
  const targetCapability = speechLanguages.find((item) => item.text_code === targetLanguage);
  const voices = targetCapability?.voices ?? [];
  const selectedVoice = voices.find((voice) => voice.name === voiceName) ?? voices[0];
  const browserRecordingSupported = typeof window !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia) && typeof MediaRecorder !== "undefined";

  useEffect(() => {
    if (sourceOptions.length && !sourceOptions.some((item) => item.locale === sourceLocale)) {
      setSourceLocale(sourceOptions[0].locale);
    }
  }, [sourceLocale, sourceOptions]);

  useEffect(() => {
    if (voices.length && !voices.some((voice) => voice.name === voiceName)) {
      setVoiceName(voices[0].name);
    }
    if (!voices.length) setVoiceName("");
  }, [voiceName, voices]);

  const clearAudio = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    setIsPlaying(false);
    setHasAudio(false);
    setAudioUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
  }, []);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const transcribe = useMutation({
    mutationFn: ({ blob, locale }: RequestPayload) => api.transcribeVoice(blob, locale),
    onSuccess: (response, variables) => {
      if (variables.requestId !== requestIdRef.current || disposedRef.current) return;
      setTranscript(response.transcript);
      setTranslation("");
      setRecordError("");
    },
    onError: (error, variables) => {
      if (variables.requestId !== requestIdRef.current || disposedRef.current) return;
      setRecordError(error instanceof Error ? error.message : t("voiceTranscriptionFailed"));
    },
  });

  const translate = useMutation({
    mutationFn: ({ text }: TranslationPayload) => api.translateText({
      source_language: sourceCapability?.text_code ?? null,
      target_language: targetLanguage,
      text,
    }),
    onSuccess: (response, variables) => {
      if (variables.requestId === translationRequestIdRef.current) setTranslation(response.translated_text);
    },
    onError: (_error, variables) => {
      if (variables.requestId === translationRequestIdRef.current) setTranslation("");
    },
  });

  const synthesize = useMutation({
    mutationFn: (_: SynthesisPayload) => api.synthesizeVoice({
      text: translation,
      locale: targetCapability?.locale ?? "",
      voice: selectedVoice?.name ?? "",
    }),
    onSuccess: (blob, variables) => {
      if (variables.requestId !== synthesisRequestIdRef.current) return;
      clearAudio();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      setHasAudio(true);
    },
    onError: (_error, variables) => {
      if (variables.requestId === synthesisRequestIdRef.current) clearAudio();
    },
  });

  const finishRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    recorder.stop();
    setRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    if (recording || transcribe.isPending) return;
    if (!browserRecordingSupported) {
      setRecordError(t("recordingUnsupported"));
      return;
    }
    setRecordError("");
    setTranscript("");
    setTranslation("");
    clearAudio();
    const supportedTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
    const mimeType = supportedTypes.find((type) => MediaRecorder.isTypeSupported(type));
    if (!mimeType) {
      setRecordError(t("recordingFormatUnsupported"));
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (disposedRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const recorder = new MediaRecorder(stream, { mimeType });
      const requestId = ++requestIdRef.current;
      cancelledRef.current = false;
      chunksRef.current = [];
      streamRef.current = stream;
      recorderRef.current = recorder;
      startedAtRef.current = Date.now();
      setElapsed(0);
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onerror = () => setRecordError(t("recordingFailed"));
      recorder.onstop = () => {
        stopStream();
        recorderRef.current = null;
        if (timerRef.current) window.clearInterval(timerRef.current);
        timerRef.current = null;
        setRecording(false);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType });
        chunksRef.current = [];
        if (cancelledRef.current || disposedRef.current || blob.size === 0) return;
        transcribe.mutate({ blob, locale: sourceLocale, requestId });
      };
      recorder.start();
      setRecording(true);
      timerRef.current = window.setInterval(() => {
        const next = Math.min(MAX_RECORDING_SECONDS, Math.floor((Date.now() - startedAtRef.current) / 1000));
        setElapsed(next);
        if (next >= MAX_RECORDING_SECONDS) finishRecording();
      }, 250);
    } catch (error) {
      stopStream();
      setRecording(false);
      const message = error instanceof DOMException && error.name === "NotAllowedError"
        ? t("microphonePermissionDenied")
        : t("microphoneUnavailable");
      setRecordError(message);
    }
  }, [browserRecordingSupported, clearAudio, finishRecording, recording, sourceLocale, stopStream, t, transcribe]);

  const cancelRecording = useCallback(() => {
    cancelledRef.current = true;
    requestIdRef.current += 1;
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    else stopStream();
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = null;
    chunksRef.current = [];
    setRecording(false);
    setElapsed(0);
    setRecordError("");
  }, [stopStream]);

  useEffect(() => () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  useEffect(() => () => {
    disposedRef.current = true;
    cancelledRef.current = true;
    if (timerRef.current) window.clearInterval(timerRef.current);
    if (recorderRef.current && recorderRef.current.state !== "inactive") recorderRef.current.stop();
    stopStream();
    audioRef.current?.pause();
  }, [stopStream]);

  const togglePlayback = () => {
    if (!audioUrl) return;
    if (!audioRef.current) {
      const audio = new Audio(audioUrl);
      audio.onended = () => setIsPlaying(false);
      audioRef.current = audio;
    }
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      void audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  };

  const stopPlayback = () => {
    audioRef.current?.pause();
    if (audioRef.current) audioRef.current.currentTime = 0;
    setIsPlaying(false);
  };

  const replayAudio = () => {
    if (!audioUrl) return;
    if (!audioRef.current) {
      const audio = new Audio(audioUrl);
      audio.onended = () => setIsPlaying(false);
      audioRef.current = audio;
    }
    audioRef.current.currentTime = 0;
    void audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
  };

  const onTranscriptChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setTranscript(event.target.value.slice(0, MAX_CHARACTERS));
    setTranslation("");
    setCopied(false);
    translationRequestIdRef.current += 1;
    synthesisRequestIdRef.current += 1;
    clearAudio();
  };

  const translateDisabled = !transcript.trim() || transcript.length > MAX_CHARACTERS || translate.isPending || !sourceCapability;
  const speechReady = capabilities.data?.provider_configured && capabilities.data.speech_recognition;
  const synthesisReady = capabilities.data?.provider_configured && capabilities.data.speech_synthesis && Boolean(selectedVoice);

  return <div className="mx-auto max-w-6xl">
    <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
      <div><p className="mb-3 text-xs font-bold uppercase tracking-[.18em] text-blue-600">VOICE</p><h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("voiceTranslator")}</h1><p className="subtle mt-2 max-w-xl text-sm leading-6 sm:text-base">{t("voiceTranslatorCopy")}</p></div>
      <div className="inline-flex items-center gap-2 self-start rounded-full border border-blue-100 bg-blue-50 px-3 py-2 text-xs font-bold text-blue-700 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-200"><Volume2 size={15} /> {t("noAudioStored")}</div>
    </div>
    {capabilities.isLoading && <VoiceNotice>{t("loadingVoiceCapabilities")}</VoiceNotice>}
    {capabilities.isError && <VoiceNotice tone="warning">{t("voiceCapabilitiesUnavailable")}</VoiceNotice>}
    {capabilities.data && !speechReady && <VoiceNotice tone="warning">{t("voiceProviderUnavailable")}</VoiceNotice>}
    <div className="mb-5 grid gap-3 md:grid-cols-[1fr_auto_1fr] md:items-end">
      <label><span className="field-label">{t("spokenLanguage")}</span><select value={sourceLocale} onChange={(event) => { requestIdRef.current += 1; translationRequestIdRef.current += 1; setSourceLocale(event.target.value); setTranscript(""); setTranslation(""); clearAudio(); }} className="voice-select">{sourceOptions.length ? sourceOptions.map((item) => <option key={item.locale} value={item.locale}>{languageName(languages.data, item)} · {item.locale}</option>) : <option value={sourceLocale}>{sourceLocale}</option>}</select></label>
      <div className="hidden h-11 items-center px-2 text-slate-300 md:flex"><CircleStop size={17} /></div>
      <label><span className="field-label">{t("translateInto")}</span><select value={targetLanguage} onChange={(event) => { translationRequestIdRef.current += 1; synthesisRequestIdRef.current += 1; setTargetLanguage(event.target.value); setTranslation(""); clearAudio(); }} className="voice-select">{targetOptions.length ? targetOptions.map((item) => <option key={item.code} value={item.code}>{item.name} · {item.code}</option>) : <option value={targetLanguage}>{targetLanguage}</option>}</select></label>
    </div>
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,.95fr)]">
      <section className="surface rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-[#13233b] sm:p-7">
        <div className="flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">{t("recording")}</p><p className="mt-1 text-sm font-semibold">{recording ? t("recordingNow") : t("pressToRecord")}</p></div><span className={`flex items-center gap-2 text-sm font-bold tabular-nums ${recording ? "text-rose-500" : "text-slate-400"}`}><span className={`h-2.5 w-2.5 rounded-full ${recording ? "animate-pulse bg-rose-500" : "bg-slate-300"}`} />{formatTime(elapsed)} / 00:15</span></div>
        <div className={`my-8 grid min-h-[190px] place-items-center rounded-2xl border ${recording ? "border-rose-200 bg-rose-50/70 dark:border-rose-900/50 dark:bg-rose-950/20" : "border-blue-100 bg-gradient-to-br from-blue-50 to-white dark:border-slate-700 dark:from-[#18345e] dark:to-[#13233b]"}`}><div className="text-center"><button aria-label={recording ? t("stopRecording") : t("startRecording")} onClick={recording ? finishRecording : startRecording} disabled={!speechReady || transcribe.isPending} className={`mx-auto grid h-20 w-20 place-items-center rounded-full text-white shadow-xl transition hover:scale-105 disabled:cursor-not-allowed disabled:opacity-40 ${recording ? "bg-rose-500 shadow-rose-500/25" : "bg-navy shadow-blue-900/20"}`}>{recording ? <Square size={27} fill="currentColor" /> : <Mic size={29} />}</button><p className="mt-4 text-xs font-semibold text-slate-500 dark:text-slate-400">{recording ? t("tapToStop") : t("microphonePermissionHint")}</p></div></div>
        <div className="flex flex-wrap justify-center gap-2">{recording && <button onClick={cancelRecording} className="voice-secondary"><X size={15} />{t("cancel")}</button>}{!recording && transcript && <button onClick={() => { setTranscript(""); setTranslation(""); clearAudio(); }} className="voice-secondary"><Trash2 size={15} />{t("clear")}</button>}</div>
        {recordError && <div role="alert" className="mt-5 flex gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100"><AlertCircle className="mt-0.5 shrink-0" size={17} /><span>{recordError}</span></div>}
        {transcribe.isPending && <div className="mt-5 flex items-center justify-center gap-2 text-sm font-semibold text-blue-600"><span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-100 border-t-blue-600" />{t("transcribing")}</div>}
      </section>
      <section className="surface rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-[#13233b] sm:p-7">
        <div className="mb-4 flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">{t("transcript")}</p><p className="mt-1 text-sm font-semibold">{t("transcriptEditable")}</p></div><span className={`text-xs ${transcript.length >= MAX_CHARACTERS ? "font-bold text-amber-600" : "subtle"}`}>{transcript.length.toLocaleString()} / {MAX_CHARACTERS.toLocaleString()}</span></div>
        <textarea aria-label={t("transcript")} value={transcript} onChange={onTranscriptChange} placeholder={t("transcriptPlaceholder")} className="min-h-[180px] w-full resize-none rounded-2xl border border-slate-100 bg-slate-50/70 p-4 text-base leading-7 text-ink outline-none placeholder:text-slate-400 focus:border-blue-300 focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-[#101d31] dark:text-white dark:placeholder:text-slate-600" />
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 dark:border-slate-700"><button disabled={translateDisabled} onClick={() => { const requestId = ++translationRequestIdRef.current; translate.mutate({ text: transcript, requestId }); }} className="inline-flex items-center gap-2 rounded-xl bg-navy px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-40">{translate.isPending ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-200 border-t-white" /> : <Volume2 size={16} />}{translate.isPending ? t("translating") : t("translate")}</button>{transcript && <button aria-label={t("copyTranscript")} onClick={() => { void navigator.clipboard?.writeText(transcript); setCopied(true); }} className="voice-secondary">{copied ? <Check size={15} /> : <Copy size={15} />}{copied ? t("copied") : t("copy")}</button>}</div>
        {translate.isError && <p role="alert" className="mt-4 text-sm font-semibold text-amber-700 dark:text-amber-200">{(translate.error as Error).message || t("translationFailed")} <button onClick={() => { const requestId = ++translationRequestIdRef.current; translate.mutate({ text: transcript, requestId }); }} className="ml-1 underline">{t("retry")}</button></p>}
        {translation && <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50/60 p-4 dark:border-blue-900/50 dark:bg-blue-950/20"><p className="mb-2 text-xs font-bold uppercase tracking-wider text-blue-600">{t("translationResult")}</p><p className="whitespace-pre-wrap text-base leading-7 dark:text-white">{translation}</p><div className="mt-4 flex flex-wrap items-center gap-2"><label className="sr-only" htmlFor="voice-select">{t("voice")}</label><select id="voice-select" value={selectedVoice?.name ?? ""} onChange={(event) => setVoiceName(event.target.value)} disabled={!voices.length} className="voice-select min-w-[190px] flex-1 bg-white dark:bg-[#13233b]">{voices.length ? voices.map((voice) => <option key={voice.name} value={voice.name}>{voice.name}</option>) : <option>{t("noVoicesAvailable")}</option>}</select><button disabled={!synthesisReady || synthesize.isPending} onClick={() => synthesize.mutate({ requestId: ++synthesisRequestIdRef.current })} className="voice-secondary disabled:cursor-not-allowed disabled:opacity-40">{synthesize.isPending ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-200 border-t-blue-600" /> : <Volume2 size={15} />}{t("generateAudio")}</button></div>{synthesize.isError && <p role="alert" className="mt-3 text-sm font-semibold text-amber-700 dark:text-amber-200">{(synthesize.error as Error).message || t("audioGenerationFailed")}</p>}</div>}
      </section>
    </div>
    {hasAudio && audioUrl && <section className="surface mt-4 flex flex-col gap-4 rounded-2xl border border-blue-100 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-[#13233b] sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-sky text-blue-600"><Volume2 size={18} /></span><div><p className="text-sm font-bold">{t("audioReady")}</p><p className="subtle text-xs">{selectedVoice?.name}</p></div></div><div className="flex gap-2"><button aria-label={isPlaying ? t("pauseAudio") : t("playAudio")} onClick={togglePlayback} className="voice-secondary">{isPlaying ? <Pause size={15} /> : <Play size={15} fill="currentColor" />}{isPlaying ? t("pause") : t("play")}</button><button onClick={replayAudio} className="voice-secondary"><RotateCcw size={15} />{t("replay")}</button><button onClick={stopPlayback} className="voice-secondary"><Square size={14} />{t("stop")}</button></div></section>}
  </div>;
}

function languageName(languages: Language[] | undefined, capability: SpeechLanguageCapability) {
  return languages?.find((language) => language.code === capability.text_code)?.name ?? capability.text_code;
}

function formatTime(seconds: number) {
  return `00:${String(seconds).padStart(2, "0")}`;
}

function VoiceNotice({ children, tone = "info" }: { children: string; tone?: "info" | "warning" }) {
  return <div className={`mb-5 rounded-2xl border p-4 text-sm ${tone === "warning" ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100" : "border-blue-100 bg-blue-50 text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-100"}`}>{children}</div>;
}
