import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Camera, Check, Clipboard, Crop, Download, ImagePlus, LoaderCircle, RotateCcw, ScanLine, Trash2, Upload, Video, X } from "lucide-react";
import { api } from "./api";
import type { OCRBlock } from "./types";

const MAX_BYTES = 8 * 1024 * 1024;
const MAX_PIXELS = 20_000_000;
const MAX_TEXT = 5000;
const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
type CropArea = { x: number; y: number; width: number; height: number };
const fullCrop: CropArea = { x: 0, y: 0, width: 1, height: 1 };

function loadImage(source: Blob | string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("The image could not be decoded."));
    image.src = typeof source === "string" ? source : URL.createObjectURL(source);
  });
}

async function renderEditedImage(file: File, rotation: number, crop: CropArea): Promise<Blob> {
  const url = URL.createObjectURL(file);
  try {
    const image = await loadImage(url);
    const sx = Math.round(image.naturalWidth * crop.x);
    const sy = Math.round(image.naturalHeight * crop.y);
    const sw = Math.max(1, Math.round(image.naturalWidth * crop.width));
    const sh = Math.max(1, Math.round(image.naturalHeight * crop.height));
    const quarterTurn = rotation % 180 !== 0;
    const canvas = document.createElement("canvas");
    canvas.width = quarterTurn ? sh : sw;
    canvas.height = quarterTurn ? sw : sh;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Image processing is unavailable in this browser.");
    context.translate(canvas.width / 2, canvas.height / 2);
    context.rotate((rotation * Math.PI) / 180);
    context.drawImage(image, sx, sy, sw, sh, -sw / 2, -sh / 2, sw, sh);
    return await new Promise<Blob>((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("The image could not be prepared.")), "image/png"));
  } finally {
    URL.revokeObjectURL(url);
  }
}

export default function CameraPage() {
  const { t } = useTranslation();
  const ocrCapabilities = useQuery({ queryKey: ["ocr-capabilities"], queryFn: api.getOcrCapabilities });
  const languages = useQuery({ queryKey: ["languages"], queryFn: api.getLanguages });
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [crop, setCrop] = useState<CropArea>(fullCrop);
  const [rotation, setRotation] = useState(0);
  const [sourceLanguage, setSourceLanguage] = useState("en");
  const [targetLanguage, setTargetLanguage] = useState("my");
  const [text, setText] = useState("");
  const [blocks, setBlocks] = useState<OCRBlock[]>([]);
  const [translation, setTranslation] = useState("");
  const [copied, setCopied] = useState<"text" | "translation" | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [cloudConsent, setCloudConsent] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textRef = useRef<HTMLTextAreaElement | null>(null);
  const sessionRef = useRef(0);
  const scanRequestRef = useRef(0);
  const translationRequestRef = useRef(0);

  const releasePreview = () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
  const stopCamera = () => { streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = null; setCameraOpen(false); };
  useEffect(() => () => { sessionRef.current += 1; stopCamera(); if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  const setImage = async (candidate: File) => {
    if (!IMAGE_TYPES.includes(candidate.type)) throw new Error(t("cameraUnsupportedType"));
    if (candidate.size > MAX_BYTES) throw new Error(t("cameraTooLarge"));
    const url = URL.createObjectURL(candidate);
    try {
      const image = await loadImage(url);
      if (image.naturalWidth * image.naturalHeight > MAX_PIXELS) throw new Error(t("cameraTooManyPixels"));
      releasePreview(); setFile(candidate); setPreviewUrl(url); setDimensions({ width: image.naturalWidth, height: image.naturalHeight }); setCrop(fullCrop); setRotation(0); setBlocks([]); setText(""); setTranslation(""); setCopied(null); sessionRef.current += 1;
    } catch (error) { URL.revokeObjectURL(url); throw error; }
  };
  const handleFiles = (items: FileList | File[]) => { const candidate = items[0]; if (!candidate) return; void setImage(candidate).catch((error) => setCameraError((error as Error).message)); };
  const onInput = (event: ChangeEvent<HTMLInputElement>) => { if (event.target.files) handleFiles(event.target.files); event.target.value = ""; };
  const onDrop = (event: DragEvent<HTMLDivElement>) => { event.preventDefault(); handleFiles(event.dataTransfer.files); };

  const startCamera = async () => {
    setCameraError("");
    try { stopCamera(); const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false }); streamRef.current = stream; setCameraOpen(true); if (videoRef.current) videoRef.current.srcObject = stream; }
    catch { setCameraError(t("cameraPermissionDenied")); }
  };
  useEffect(() => { if (cameraOpen && videoRef.current && streamRef.current) { videoRef.current.srcObject = streamRef.current; void videoRef.current.play(); } }, [cameraOpen]);
  useEffect(() => { const available = ocrCapabilities.data?.languages ?? []; if (available.length && !available.includes(sourceLanguage)) setSourceLanguage(available[0]); }, [ocrCapabilities.data?.languages, sourceLanguage]);
  const capture = () => { const video = videoRef.current; if (!video || !video.videoWidth) return; const canvas = document.createElement("canvas"); canvas.width = video.videoWidth; canvas.height = video.videoHeight; canvas.getContext("2d")?.drawImage(video, 0, 0); canvas.toBlob((blob) => { if (blob) void setImage(new File([blob], "camera-capture.png", { type: "image/png" })).catch((error) => setCameraError((error as Error).message)); stopCamera(); }, "image/png"); };

  const scan = useMutation({ mutationFn: async ({ image, language, consent }: { image: Blob; language: string; consent: boolean; requestId: number }) => api.extractOcr(image, language, consent), onSuccess: (result, variables) => { if (variables.requestId !== scanRequestRef.current || sessionRef.current === 0) return; setText(result.text.slice(0, MAX_TEXT)); setBlocks(result.blocks); setTranslation(""); }, onError: () => { if (scanRequestRef.current) setBlocks([]); } });
  const translate = useMutation({ mutationFn: (variables: { source_language: string | null; target_language: string; text: string; requestId: number }) => api.translateText({ source_language: variables.source_language, target_language: variables.target_language, text: variables.text }), onSuccess: (result, variables) => { if (variables.requestId !== translationRequestRef.current) return; setTranslation(result.translated_text); }, onError: () => setTranslation("") });
  const scanImage = async () => { if (!file || scan.isPending || !ocrCapabilities.data?.provider_configured || (ocrCapabilities.data.consent_required && !cloudConsent)) return; const requestId = ++scanRequestRef.current; const token = sessionRef.current; const prepared = await renderEditedImage(file, rotation, crop); if (token !== sessionRef.current || requestId !== scanRequestRef.current) return; const processedFile = new File([prepared], "lingua-ocr.png", { type: "image/png" }); const nextUrl = URL.createObjectURL(processedFile); releasePreview(); setFile(processedFile); setPreviewUrl(nextUrl); setCrop(fullCrop); setRotation(0); scan.mutate({ image: processedFile, language: sourceLanguage, consent: cloudConsent, requestId }); };
  const clear = () => { sessionRef.current += 1; scanRequestRef.current += 1; translationRequestRef.current += 1; scan.reset(); translate.reset(); stopCamera(); releasePreview(); setFile(null); setPreviewUrl(null); setDimensions({ width: 0, height: 0 }); setCrop(fullCrop); setRotation(0); setText(""); setBlocks([]); setTranslation(""); setCopied(null); setCameraError(""); };
  const copy = async (value: string, kind: "text" | "translation") => { if (!value) return; await navigator.clipboard?.writeText(value); setCopied(kind); };
  const exportText = () => { if (!text) return; const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" })); const anchor = document.createElement("a"); anchor.href = url; anchor.download = "lingua-ocr.txt"; anchor.click(); URL.revokeObjectURL(url); };
  const ocrLanguages = ocrCapabilities.data?.languages ?? [];
  const cloudConsentRequired = Boolean(ocrCapabilities.data?.consent_required);
  const targetLanguages = languages.data ?? [];
  const canTranslate = Boolean(text.trim()) && text.length <= MAX_TEXT && targetLanguage !== sourceLanguage && !translate.isPending;
  const scanError = scan.error as Error | null;
  const translateError = translate.error as Error | null;

  return <div className="mx-auto max-w-6xl"><div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="mb-3 text-xs font-bold uppercase tracking-[.18em] text-blue-600">CAMERA</p><h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("cameraTitle")}</h1><p className="subtle mt-2 max-w-2xl text-sm leading-6">{t("cameraCopy")}</p></div><button onClick={clear} disabled={!file && !text && !translation} className="inline-flex items-center gap-2 self-start rounded-xl border border-slate-200 px-3 py-2 text-xs font-bold disabled:opacity-40 dark:border-slate-700"><Trash2 size={14} />{t("clear")}</button></div>
    <div className="mb-5 rounded-2xl border border-blue-100 bg-blue-50/70 p-4 text-sm text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/20 dark:text-blue-100"><ScanLine className="mr-2 inline" size={16} />{t("cameraReviewNotice")}</div>
    {ocrCapabilities.isLoading && <Notice text={t("cameraLoadingCapabilities")} />}{ocrCapabilities.isError && <Notice text={t("cameraCapabilitiesError")} tone="warning" />}{ocrCapabilities.data && !ocrCapabilities.data.provider_configured && <Notice text={t("cameraProviderUnavailable")} tone="warning" />}{cloudConsentRequired && <label className="mb-5 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100"><input type="checkbox" checked={cloudConsent} onChange={(event) => setCloudConsent(event.target.checked)} className="mt-1" />{t("cameraCloudConsent")}</label>}{cameraError && <Notice text={cameraError} tone="warning" />}
    <div className="mb-4 max-w-sm"><label><span className="field-label">{t("source")}</span><select value={sourceLanguage} onChange={(event) => setSourceLanguage(event.target.value)} className="voice-select" disabled={!ocrLanguages.length}>{ocrLanguages.length ? ocrLanguages.map((code) => <option key={code} value={code}>{code}</option>) : <option value={sourceLanguage}>{sourceLanguage}</option>}</select></label></div>
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,.92fr)]"><section className="surface rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-[#13233b] sm:p-7"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">{t("cameraImage")}</p><p className="mt-1 text-sm font-semibold">{dimensions.width ? `${dimensions.width} × ${dimensions.height}` : t("cameraNoImage")}</p></div><div className="flex flex-wrap gap-2"><button onClick={() => fileInputRef.current?.click()} className="camera-secondary"><Upload size={15} />{t("cameraUpload")}</button><button onClick={() => void startCamera()} className="camera-secondary"><Video size={15} />{t("cameraCapture")}</button><input ref={fileInputRef} type="file" accept={IMAGE_TYPES.join(",")} className="hidden" onChange={onInput} /></div></div>
      {!previewUrl ? <div onDragOver={(event) => event.preventDefault()} onDrop={onDrop} className="grid min-h-[330px] place-items-center rounded-2xl border-2 border-dashed border-blue-200 bg-gradient-to-br from-blue-50 to-white p-8 text-center dark:border-blue-900/60 dark:from-[#18345e] dark:to-[#13233b]"><div><ImagePlus className="mx-auto mb-4 text-blue-500" size={34} /><p className="font-bold">{t("cameraDropHere")}</p><p className="subtle mt-1 text-sm">{t("cameraFormats")}</p><button onClick={() => fileInputRef.current?.click()} className="mt-5 rounded-xl bg-navy px-4 py-2.5 text-sm font-bold text-white"><Upload size={15} className="mr-2 inline" />{t("cameraUpload")}</button></div></div> : <><div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-[#101d31]"><img src={previewUrl} alt={t("cameraPreviewAlt")} className="mx-auto max-h-[420px] w-full object-contain transition-transform" style={{ transform: `rotate(${rotation}deg)` }} />{blocks.map((block, index) => <span key={`${block.left}-${block.top}-${index}`} className="pointer-events-none absolute border-2 border-blue-400 bg-blue-400/10" style={{ left: `${block.left * 100}%`, top: `${block.top * 100}%`, width: `${block.width * 100}%`, height: `${block.height * 100}%` }} aria-hidden="true" />)}<div className="pointer-events-none absolute border-2 border-dashed border-white/90 shadow-[0_0_0_9999px_rgba(15,23,42,.28)]" style={{ left: `${crop.x * 100}%`, top: `${crop.y * 100}%`, width: `${crop.width * 100}%`, height: `${crop.height * 100}%` }} /></div><div className="mt-4 flex flex-wrap items-center gap-2"><button onClick={() => setRotation((value) => (value + 90) % 360)} className="camera-secondary"><RotateCcw size={15} />{t("cameraRotate")}</button><button onClick={() => setCrop(fullCrop)} className="camera-secondary"><Crop size={15} />{t("cameraResetCrop")}</button><button onClick={() => { setFile(null); releasePreview(); setPreviewUrl(null); setBlocks([]); setText(""); setTranslation(""); }} className="camera-secondary"><X size={15} />{t("cameraRemove")}</button></div><div className="mt-4 grid gap-3 sm:grid-cols-2"><CropSlider label={t("cameraCropLeft")} value={crop.x} onChange={(value) => setCrop((current) => ({ ...current, x: Math.min(value, 1 - current.width) }))} /><CropSlider label={t("cameraCropTop")} value={crop.y} onChange={(value) => setCrop((current) => ({ ...current, y: Math.min(value, 1 - current.height) }))} /><CropSlider label={t("cameraCropWidth")} value={crop.width} min={0.1} onChange={(value) => setCrop((current) => ({ ...current, width: Math.min(value, 1 - current.x) }))} /><CropSlider label={t("cameraCropHeight")} value={crop.height} min={0.1} onChange={(value) => setCrop((current) => ({ ...current, height: Math.min(value, 1 - current.y) }))} /></div></>}
      {cameraOpen && <div className="mt-4 rounded-2xl border border-blue-200 bg-slate-950 p-3 dark:border-blue-900"><video ref={videoRef} muted playsInline className="max-h-72 w-full rounded-xl object-contain" aria-label={t("cameraLivePreview")} /><div className="mt-3 flex justify-center gap-2"><button onClick={capture} className="camera-primary"><Camera size={16} />{t("cameraTakePhoto")}</button><button onClick={stopCamera} className="camera-secondary"><X size={15} />{t("cancel")}</button></div></div>}
      <button onClick={() => void scanImage()} disabled={!file || scan.isPending || !ocrCapabilities.data?.provider_configured || (cloudConsentRequired && !cloudConsent)} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-navy px-4 py-3 text-sm font-bold text-white hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-40">{scan.isPending ? <LoaderCircle className="animate-spin" size={17} /> : <ScanLine size={17} />}{scan.isPending ? t("cameraScanning") : t("cameraScan")}</button>{scanError && <ErrorNotice message={scanError.message} onRetry={() => void scanImage()} retryLabel={t("retry")} />}</section>
      <section className="surface rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-[#13233b] sm:p-7"><div className="mb-4 flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">{t("cameraExtractedText")}</p><p className="mt-1 text-sm font-semibold">{t("cameraEditableReview")}</p></div><span className={`text-xs ${text.length >= MAX_TEXT ? "font-bold text-amber-600" : "subtle"}`}>{text.length.toLocaleString()} / {MAX_TEXT.toLocaleString()}</span></div><textarea ref={textRef} value={text} onChange={(event) => { setText(event.target.value.slice(0, MAX_TEXT)); setTranslation(""); translationRequestRef.current += 1; }} placeholder={t("cameraTextPlaceholder")} aria-label={t("cameraExtractedText")} className="min-h-[220px] w-full resize-y rounded-2xl border border-slate-100 bg-slate-50/70 p-4 text-base leading-7 outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-[#101d31] dark:text-white" /><div className="mt-3 flex flex-wrap gap-2"><button onClick={() => textRef.current?.select()} disabled={!text} className="camera-secondary disabled:opacity-40">{t("cameraSelectAll")}</button><button onClick={() => void copy(text, "text")} disabled={!text} className="camera-secondary disabled:opacity-40">{copied === "text" ? <Check size={15} /> : <Clipboard size={15} />}{copied === "text" ? t("copied") : t("copy")}</button><button onClick={exportText} disabled={!text} className="camera-secondary disabled:opacity-40"><Download size={15} />TXT</button></div><div className="my-6 border-t border-slate-100 dark:border-slate-700" /><label><span className="field-label">{t("target")}</span><select value={targetLanguage} onChange={(event) => { setTargetLanguage(event.target.value); setTranslation(""); }} className="voice-select w-full">{targetLanguages.filter((language) => language.is_target_enabled).map((language) => <option key={language.code} value={language.code}>{language.name} · {language.code}</option>)}</select></label><button onClick={() => { const requestId = ++translationRequestRef.current; translate.mutate({ source_language: sourceLanguage, target_language: targetLanguage, text, requestId } as typeof translate extends never ? never : { source_language: string; target_language: string; text: string; requestId: number }); }} disabled={!canTranslate} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-navy px-4 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-40">{translate.isPending ? <LoaderCircle className="animate-spin" size={17} /> : <ScanLine size={17} />}{translate.isPending ? t("translating") : t("cameraTranslate")}</button>{translateError && <ErrorNotice message={translateError.message} onRetry={() => { const requestId = ++translationRequestRef.current; translate.mutate({ source_language: sourceLanguage, target_language: targetLanguage, text, requestId } as never); }} retryLabel={t("retry")} />}{translation && <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50/60 p-4 dark:border-blue-900/50 dark:bg-blue-950/20"><p className="mb-2 text-xs font-bold uppercase tracking-wider text-blue-600">{t("cameraTranslationResult")}</p><p className="whitespace-pre-wrap text-base leading-7 dark:text-white">{translation}</p><button onClick={() => void copy(translation, "translation")} className="camera-secondary mt-4">{copied === "translation" ? <Check size={15} /> : <Clipboard size={15} />}{copied === "translation" ? t("copied") : t("copy")}</button></div>}</section></div>
  </div>;
}

function CropSlider({ label, value, min = 0, onChange }: { label: string; value: number; min?: number; onChange: (value: number) => void }) { return <label><span className="field-label">{label} · {Math.round(value * 100)}%</span><input aria-label={label} type="range" min={min} max="1" step="0.01" value={value} onChange={(event) => onChange(Number(event.target.value))} className="w-full accent-blue-600" /></label>; }
function Notice({ text, tone = "info" }: { text: string; tone?: "info" | "warning" }) { return <div role="status" className={`mb-5 rounded-2xl border p-4 text-sm ${tone === "warning" ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100" : "border-blue-100 bg-blue-50 text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/20 dark:text-blue-100"}`}>{text}</div>; }
function ErrorNotice({ message, onRetry, retryLabel }: { message: string; onRetry: () => void; retryLabel: string }) { return <div role="alert" className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100"><p>{message}</p><button onClick={onRetry} className="mt-2 font-bold underline">{retryLabel}</button></div>; }
