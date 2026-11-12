import { useEffect, useMemo, useRef, useState } from "react";
import type { DragEvent, ReactNode, RefObject } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  LoaderCircle,
  RotateCcw,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import { api } from "./api";
import type { DocumentJob, DocumentSegment, Language } from "./types";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = ["pdf", "docx", "txt"] as const;
type PreviewTab = "original" | "translated";

export default function DocumentPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [targetLanguage, setTargetLanguage] = useState("my");
  const [jobId, setJobId] = useState<string | null>(null);
  const [uploadedJob, setUploadedJob] = useState<DocumentJob | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [draftSegments, setDraftSegments] = useState<DocumentSegment[]>([]);
  const [activePage, setActivePage] = useState(1);
  const [previewTab, setPreviewTab] = useState<PreviewTab>("original");
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const languagesQuery = useQuery({ queryKey: ["languages"], queryFn: api.getLanguages });
  const languages = languagesQuery.data ?? [];
  const jobQuery = useQuery({
    queryKey: ["document", jobId],
    queryFn: () => api.getDocument(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ["completed", "failed", "cancelled", "expired", "awaiting_review"].includes(status) ? false : 1500;
    },
  });
  const job = jobQuery.data ?? uploadedJob;
  const segmentsQuery = useQuery({
    queryKey: ["document-segments", jobId],
    queryFn: () => api.getDocumentSegments(jobId as string),
    enabled: Boolean(jobId && job && ["awaiting_review", "translating", "exporting", "completed", "failed"].includes(job.status)),
    refetchInterval: job && ["translating", "exporting"].includes(job.status) ? 1500 : false,
  });

  useEffect(() => {
    if (segmentsQuery.data?.segments) setDraftSegments(segmentsQuery.data.segments);
  }, [segmentsQuery.data]);
  useEffect(() => {
    if (job?.source_language) setSourceLanguage(job.source_language);
    if (job?.target_language) setTargetLanguage(job.target_language);
    if (job?.status === "awaiting_review") setPreviewTab("original");
  }, [job?.source_language, job?.target_language, job?.status]);

  const uploadMutation = useMutation({
    mutationFn: ({ selectedFile, source }: { selectedFile: File; source: string | null }) => api.uploadDocument(selectedFile, source, setUploadProgress),
    onSuccess: (newJob) => {
      setUploadedJob(newJob);
      setJobId(newJob.id);
      setUploadProgress(100);
      setLocalError(null);
    },
  });
  const updateSegmentsMutation = useMutation({
    mutationFn: (segments: DocumentSegment[]) => api.updateDocumentSegments(jobId as string, segments),
    onSuccess: (response) => {
      setDraftSegments(response.segments);
      queryClient.setQueryData(["document-segments", jobId], response);
    },
  });
  const translateMutation = useMutation({
    mutationFn: async () => {
      const reviewedSegments = draftSegments.map(({ translated_text: _translated, ...segment }) => ({ ...segment, translated_text: null }));
      await api.updateDocumentSegments(jobId as string, reviewedSegments);
      return api.translateDocument(jobId as string, {
        source_language: sourceLanguage === "auto" ? null : sourceLanguage,
        target_language: targetLanguage,
        reviewed: true,
      }, `document-${jobId}-${sourceLanguage}-${targetLanguage}`);
    },
    onSuccess: (translatedJob) => {
      setUploadedJob(translatedJob);
      void queryClient.invalidateQueries({ queryKey: ["document", jobId] });
      void queryClient.invalidateQueries({ queryKey: ["document-segments", jobId] });
    },
  });
  const cancelMutation = useMutation({
    mutationFn: () => api.cancelDocument(jobId as string),
    onSuccess: (cancelledJob) => { setUploadedJob(cancelledJob); void queryClient.invalidateQueries({ queryKey: ["document", jobId] }); },
  });
  const retryMutation = useMutation({
    mutationFn: () => api.retryDocument(jobId as string),
    onSuccess: (retriedJob) => { setUploadedJob(retriedJob); void queryClient.invalidateQueries({ queryKey: ["document", jobId] }); },
  });
  const deleteMutation = useMutation({
    mutationFn: () => api.deleteDocument(jobId as string),
    onSuccess: () => { queryClient.removeQueries({ queryKey: ["document", jobId] }); queryClient.removeQueries({ queryKey: ["document-segments", jobId] }); resetSession(); },
  });

  const pages = useMemo(() => Array.from(new Set(draftSegments.map((segment) => segment.page).filter((page): page is number => page !== null))).sort((a, b) => a - b), [draftSegments]);
  const visibleSegments = pages.length ? draftSegments.filter((segment) => segment.page === pages[activePage - 1]) : draftSegments;
  const terminal = Boolean(job && ["completed", "failed", "cancelled", "expired"].includes(job.status));
  const busy = uploadMutation.isPending || updateSegmentsMutation.isPending || translateMutation.isPending || cancelMutation.isPending || retryMutation.isPending || deleteMutation.isPending;

  function resetSession() {
    setFile(null); setJobId(null); setUploadedJob(null); setDraftSegments([]); setUploadProgress(0); setActivePage(1); setLocalError(null);
    if (fileInput.current) fileInput.current.value = "";
  }
  async function chooseFile(nextFile: File | null) {
    if (!nextFile) return;
    const validation = await validateDocument(nextFile);
    if (validation) { setLocalError(validation); setFile(null); return; }
    setFile(nextFile); setLocalError(null); setJobId(null); setUploadedJob(null); setDraftSegments([]); setUploadProgress(0);
  }
  function upload() {
    if (!file || uploadMutation.isPending) return;
    uploadMutation.mutate({ selectedFile: file, source: sourceLanguage === "auto" ? null : sourceLanguage });
  }
  function editSegment(id: string, value: string) {
    setDraftSegments((current) => current.map((segment) => segment.id === id ? { ...segment, source_text: value, translated_text: null } : segment));
  }
  function updateReviewedText() {
    if (!jobId || updateSegmentsMutation.isPending) return;
    updateSegmentsMutation.mutate(draftSegments.map(({ translated_text: _translated, ...segment }) => ({ ...segment, translated_text: null })));
  }
  async function download(format: "pdf" | "docx" | "txt") {
    if (!jobId || job?.document_format !== format) return;
    try {
      const result = await api.downloadDocument(jobId);
      const url = URL.createObjectURL(result.blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = result.filename; anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { setLocalError(error instanceof Error ? error.message : t("documentDownloadFailed")); }
  }

  return <div className="mx-auto max-w-6xl">
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div><p className="mb-3 text-xs font-bold uppercase tracking-[.18em] text-blue-600">{t("documentsEyebrow")}</p><h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("documentTranslator")}</h1><p className="subtle mt-2 max-w-2xl text-sm leading-6 sm:text-base">{t("documentTranslatorCopy")}</p></div>
      {job && <button onClick={() => deleteMutation.mutate()} disabled={busy} className="voice-secondary self-start sm:self-auto"><Trash2 size={15} />{t("deleteDocument")}</button>}
    </div>
    {!job && <UploadPanel file={file} dragging={dragging} error={localError ?? (uploadMutation.error instanceof Error ? uploadMutation.error.message : null)} progress={uploadProgress} sourceLanguage={sourceLanguage} targetLanguage={targetLanguage} languages={languages} loadingLanguages={languagesQuery.isLoading} onSourceChange={setSourceLanguage} onTargetChange={setTargetLanguage} onChoose={(next) => void chooseFile(next)} onDrop={(event) => { event.preventDefault(); setDragging(false); void chooseFile(event.dataTransfer.files[0] ?? null); }} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} inputRef={fileInput} onUpload={upload} uploading={uploadMutation.isPending} onClear={() => { setFile(null); setLocalError(null); }} />}
    {job && <DocumentWorkspace job={job} segments={draftSegments} visibleSegments={visibleSegments} pages={pages} activePage={activePage} previewTab={previewTab} sourceLanguage={sourceLanguage} targetLanguage={targetLanguage} languages={languages} error={localError ?? (jobQuery.error instanceof Error ? jobQuery.error.message : null) ?? (segmentsQuery.error instanceof Error ? segmentsQuery.error.message : null) ?? (translateMutation.error instanceof Error ? translateMutation.error.message : null)} languagesLoading={languagesQuery.isLoading} terminal={terminal} busy={busy} onSourceChange={setSourceLanguage} onTargetChange={setTargetLanguage} onEdit={editSegment} onPage={(page) => setActivePage(page)} onTab={setPreviewTab} onSaveReview={updateReviewedText} onTranslate={() => translateMutation.mutate()} onCancel={() => cancelMutation.mutate()} onRetry={() => retryMutation.mutate()} onDownload={download} onReset={resetSession} />}
  </div>;
}

function UploadPanel({ file, dragging, error, progress, sourceLanguage, targetLanguage, languages, loadingLanguages, onSourceChange, onTargetChange, onChoose, onDrop, onDragOver, onDragLeave, inputRef, onUpload, uploading, onClear }: { file: File | null; dragging: boolean; error: string | null; progress: number; sourceLanguage: string; targetLanguage: string; languages: Language[]; loadingLanguages: boolean; onSourceChange: (value: string) => void; onTargetChange: (value: string) => void; onChoose: (file: File | null) => void; onDrop: (event: DragEvent<HTMLDivElement>) => void; onDragOver: (event: DragEvent<HTMLDivElement>) => void; onDragLeave: () => void; inputRef: RefObject<HTMLInputElement>; onUpload: () => void; uploading: boolean; onClear: () => void }) {
  const { t } = useTranslation();
  return <section className="space-y-5">
    <div onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave} className={`rounded-3xl border-2 border-dashed p-6 text-center transition sm:p-12 ${dragging ? "border-blue-500 bg-blue-50 dark:bg-blue-950/20" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-[#13233b]"}`}>
      <input ref={inputRef} aria-label={t("chooseDocumentFile")} className="sr-only" type="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" onChange={(event) => onChoose(event.target.files?.[0] ?? null)} />
      <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-sky text-blue-600"><UploadCloud size={25} /></div><h2 className="mt-5 text-lg font-bold">{t("dropDocument")}</h2><p className="subtle mt-2 text-sm">{t("documentFormats")}</p><button onClick={() => inputRef.current?.click()} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-navy px-4 py-3 text-sm font-bold text-white hover:bg-blue-900"><FileText size={16} />{t("chooseDocument")}</button>
    </div>
    {error && <ErrorBanner message={error} />}
    <div className="grid gap-4 md:grid-cols-2"><LanguageField label={t("sourceLanguage")} value={sourceLanguage} languages={languages} loading={loadingLanguages} auto onChange={onSourceChange} /><LanguageField label={t("targetLanguage")} value={targetLanguage} languages={languages} loading={loadingLanguages} onChange={onTargetChange} /></div>
    {file && <div className="surface flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-[#13233b] sm:flex-row sm:items-center sm:justify-between"><div className="flex min-w-0 items-center gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-sky text-blue-600"><FileText size={18} /></div><div className="min-w-0"><p className="truncate text-sm font-bold">{file.name}</p><p className="subtle mt-1 text-xs">{formatBytes(file.size)} · {file.type || t("unknownType")}</p></div></div><div className="flex items-center gap-2"><button onClick={onClear} disabled={uploading} className="voice-secondary"><X size={14} />{t("clear")}</button><button onClick={onUpload} disabled={uploading} className="inline-flex items-center justify-center gap-2 rounded-xl bg-navy px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-50">{uploading && <LoaderCircle className="animate-spin" size={15} />}{uploading ? `${t("uploading")} ${progress}%` : t("uploadDocument")}</button></div></div>}
  </section>;
}

function DocumentWorkspace({ job, segments, visibleSegments, pages, activePage, previewTab, sourceLanguage, targetLanguage, languages, error, languagesLoading, terminal, busy, onSourceChange, onTargetChange, onEdit, onPage, onTab, onSaveReview, onTranslate, onCancel, onRetry, onDownload, onReset }: { job: DocumentJob; segments: DocumentSegment[]; visibleSegments: DocumentSegment[]; pages: number[]; activePage: number; previewTab: PreviewTab; sourceLanguage: string; targetLanguage: string; languages: Language[]; error: string | null; languagesLoading: boolean; terminal: boolean; busy: boolean; onSourceChange: (value: string) => void; onTargetChange: (value: string) => void; onEdit: (id: string, value: string) => void; onPage: (page: number) => void; onTab: (tab: PreviewTab) => void; onSaveReview: () => void; onTranslate: () => void; onCancel: () => void; onRetry: () => void; onDownload: (format: "pdf" | "docx" | "txt") => void; onReset: () => void }) {
  const { t } = useTranslation();
  const canTranslate = job.status === "awaiting_review" && segments.length > 0 && Boolean(targetLanguage) && sourceLanguage !== targetLanguage && !busy;
  const isTranslating = ["translating", "exporting"].includes(job.status);
  return <div className="space-y-5">
    <section className="surface rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-[#13233b] sm:p-5"><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div className="flex min-w-0 items-start gap-3"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-sky text-blue-600"><FileText size={20} /></div><div className="min-w-0"><h2 className="truncate font-bold">{job.original_filename}</h2><p className="subtle mt-1 text-xs">{formatBytes(job.size_bytes)} · {job.document_format.toUpperCase()} · {t("expires")} {new Date(job.expires_at).toLocaleString()}</p></div></div><StatusBadge status={job.status} /></div><div className="mt-5"><div className="mb-2 flex justify-between text-xs font-semibold text-slate-500"><span>{statusLabel(job.status, t)}</span><span>{job.progress}%</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${job.progress}%` }} /></div></div></section>
    {error && <ErrorBanner message={error} />}
    {job.status === "expired" && <EmptyState icon={<AlertTriangle size={25} />} title={t("documentExpired")} copy={t("documentExpiredCopy")} action={<button onClick={onReset} className="voice-secondary"><UploadCloud size={15} />{t("uploadAnother")}</button>} />}
    {job.status === "failed" && <div className="flex flex-wrap gap-2"><button onClick={onRetry} disabled={busy} className="inline-flex items-center gap-2 rounded-xl bg-navy px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50"><RotateCcw size={15} />{t("retry")}</button><button onClick={onReset} className="voice-secondary">{t("uploadAnother")}</button></div>}
    {job.status === "cancelled" && <EmptyState icon={<AlertTriangle size={25} />} title={t("documentCancelled")} copy={t("documentCancelledCopy")} action={<button onClick={onReset} className="voice-secondary"><UploadCloud size={15} />{t("uploadAnother")}</button>} />}
    {!(["queued", "extracting"].includes(job.status)) && job.status !== "expired" && job.status !== "cancelled" && <>
      <div className="grid gap-4 md:grid-cols-2"><LanguageField label={t("sourceLanguage")} value={sourceLanguage} languages={languages} loading={languagesLoading} auto onChange={onSourceChange} /><LanguageField label={t("targetLanguage")} value={targetLanguage} languages={languages} loading={languagesLoading} onChange={onTargetChange} /></div>
      <section className="surface rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-[#13233b] sm:p-5"><div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-bold">{t("reviewExtractedText")}</h2><p className="subtle mt-1 text-xs">{t("reviewExtractedTextCopy")}</p></div>{pages.length > 0 && <div className="flex items-center gap-2"><button aria-label={t("previousPage")} onClick={() => onPage(Math.max(1, activePage - 1))} disabled={activePage <= 1} className="voice-secondary p-2"><ChevronLeft size={15} /></button><span className="text-xs font-bold text-slate-500">{t("page")} {activePage} / {pages.length}</span><button aria-label={t("nextPage")} onClick={() => onPage(Math.min(pages.length, activePage + 1))} disabled={activePage >= pages.length} className="voice-secondary p-2"><ChevronRight size={15} /></button></div>}</div><div className="mb-4 grid grid-cols-2 rounded-xl bg-slate-100 p-1 dark:bg-slate-800 sm:hidden"><TabButton active={previewTab === "original"} onClick={() => onTab("original")}>{t("original")}</TabButton><TabButton active={previewTab === "translated"} onClick={() => onTab("translated")}>{t("translated")}</TabButton></div><div className="grid gap-4 md:grid-cols-2"><PreviewColumn hiddenOnMobile={previewTab !== "original"} title={t("original")}><div className="space-y-3">{visibleSegments.length ? visibleSegments.map((segment) => <div key={segment.id} className="rounded-xl border border-slate-100 p-3 dark:border-slate-700"><textarea aria-label={`${t("original")} ${segment.index + 1}`} value={segment.source_text} onChange={(event) => onEdit(segment.id, event.target.value)} disabled={job.status !== "awaiting_review"} className="min-h-[72px] w-full resize-y bg-transparent text-sm leading-6 outline-none disabled:opacity-80" /></div>) : <p className="subtle py-10 text-center text-sm">{t("noExtractedText")}</p>}</div></PreviewColumn><PreviewColumn hiddenOnMobile={previewTab !== "translated"} title={t("translated")}><div className="space-y-3">{visibleSegments.length ? visibleSegments.map((segment) => <div key={segment.id} className="min-h-[98px] rounded-xl border border-blue-100 bg-blue-50/60 p-3 text-sm leading-6 dark:border-blue-900/40 dark:bg-blue-950/20">{segment.translated_text || (isTranslating ? <span className="subtle inline-flex items-center gap-2"><LoaderCircle className="animate-spin" size={14} />{t("translatingDocument")}</span> : <span className="subtle">{t("translationWillAppear")}</span>)}</div>) : <p className="subtle py-10 text-center text-sm">{t("translationWillAppear")}</p>}</div></PreviewColumn></div></section>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">{!terminal && <button onClick={onCancel} disabled={busy || !["queued", "extracting", "translating", "exporting"].includes(job.status)} className="voice-secondary self-start"><X size={15} />{t("cancelJob")}</button>}<div className="flex flex-wrap gap-2 sm:ml-auto">{job.status === "awaiting_review" && <button onClick={onSaveReview} disabled={busy} className="voice-secondary"><Check size={15} />{t("saveReview")}</button>}<button onClick={onTranslate} disabled={!canTranslate} className="inline-flex items-center justify-center gap-2 rounded-xl bg-navy px-4 py-2.5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-40">{isTranslating && <LoaderCircle className="animate-spin" size={15} />}{isTranslating ? t("translatingDocument") : t("translateDocument")}</button></div></div>
      {job.status === "completed" && <DownloadPanel job={job} onDownload={onDownload} />}
    </>}
  </div>;
}

function DownloadPanel({ job, onDownload }: { job: DocumentJob; onDownload: (format: "pdf" | "docx" | "txt") => void }) { const { t } = useTranslation(); return <section className="rounded-2xl border border-blue-100 bg-blue-50/70 p-4 dark:border-blue-900/40 dark:bg-blue-950/20"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-bold">{t("documentReady")}</p><p className="subtle mt-1 text-xs">{t("documentDownloadFormat", { format: job.document_format.toUpperCase() })}</p></div><div className="flex flex-wrap gap-2">{(["pdf", "docx", "txt"] as const).map((format) => <button key={format} onClick={() => onDownload(format)} disabled={job.document_format !== format} className="voice-secondary disabled:cursor-not-allowed disabled:opacity-40"><Download size={14} />{t("downloadFormat", { format: format.toUpperCase() })}</button>)}</div></div></section>; }
function LanguageField({ label, value, languages, loading, auto = false, onChange }: { label: string; value: string; languages: Language[]; loading: boolean; auto?: boolean; onChange: (value: string) => void }) { return <label className="relative"><span className="field-label">{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)} disabled={loading} className="voice-select">{auto && <option value="auto">Auto Detect</option>}{languages.map((language) => <option key={language.code} value={language.code}>{language.name} · {language.code}</option>)}</select></label>; }
function PreviewColumn({ title, hiddenOnMobile, children }: { title: string; hiddenOnMobile: boolean; children: ReactNode }) { return <div className={`${hiddenOnMobile ? "hidden md:block" : "block"}`}><p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">{title}</p>{children}</div>; }
function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) { return <button onClick={onClick} className={`rounded-lg px-3 py-2 text-xs font-bold ${active ? "bg-white text-navy shadow-sm dark:bg-[#13233b] dark:text-white" : "text-slate-500"}`}>{children}</button>; }
function StatusBadge({ status }: { status: DocumentJob["status"] }) { const { t } = useTranslation(); return <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 dark:bg-blue-950/40 dark:text-blue-200"><span className="h-1.5 w-1.5 rounded-full bg-blue-500" />{statusLabel(status, t)}</span>; }
function statusLabel(status: DocumentJob["status"], t: (key: string) => string) { return ({ queued: t("queued"), extracting: t("extracting"), awaiting_review: t("awaitingReview"), translating: t("translatingDocument"), exporting: t("exporting"), completed: t("completed"), failed: t("failed"), cancelled: t("cancelled"), expired: t("expired") })[status]; }
function ErrorBanner({ message }: { message: string }) { return <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100"><p className="font-bold">{message}</p></div>; }
function EmptyState({ icon, title, copy, action }: { icon: ReactNode; title: string; copy: string; action: ReactNode }) { return <div className="surface rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-slate-700 dark:bg-[#13233b]"><div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-sky text-blue-600">{icon}</div><h2 className="font-bold">{title}</h2><p className="subtle mx-auto mt-2 max-w-md text-sm">{copy}</p><div className="mt-5">{action}</div></div>; }
function formatBytes(bytes: number) { if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`; return `${(bytes / 1024 / 1024).toFixed(1)} MB`; }
async function validateDocument(file: File): Promise<string | null> { if (!file.size) return "The selected document is empty."; if (file.size > MAX_BYTES) return "Documents must be 10 MB or smaller."; const extension = file.name.split(".").pop()?.toLowerCase(); if (!extension || !ACCEPTED_EXTENSIONS.includes(extension as typeof ACCEPTED_EXTENSIONS[number])) return "Only PDF, DOCX, and UTF-8 TXT files are supported."; const data = await readFile(file); const bytes = new Uint8Array(data.slice(0, 4)); if (extension === "pdf" && new TextDecoder().decode(bytes) !== "%PDF") return "The PDF signature is invalid."; if (extension === "docx" && !(bytes[0] === 0x50 && bytes[1] === 0x4b)) return "The DOCX archive signature is invalid."; if (extension === "txt") { try { new TextDecoder("utf-8", { fatal: true }).decode(data); } catch { return "The TXT file must be valid UTF-8."; } } return null; }
function readFile(file: Blob): Promise<ArrayBuffer> { if (typeof file.arrayBuffer === "function") return file.arrayBuffer(); return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result as ArrayBuffer); reader.onerror = () => reject(reader.error ?? new Error("Could not read file")); reader.readAsArrayBuffer(file); }); }
