import { ApiRequestError } from "./types";
import type { ApiError, Capabilities, DocumentJob, DocumentSegment, DocumentSegmentsResponse, Language, OCRCapabilities, OCRResponse, SpeechCapabilities, TranslationResponse, VoiceTranscriptionResponse } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const documentCapabilityToken = import.meta.env.VITE_DOCUMENT_CAPABILITY_TOKEN as string | undefined;

function documentHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return documentCapabilityToken
    ? { "X-Document-Capability-Token": documentCapabilityToken, ...extra }
    : extra;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiError;
    throw new ApiRequestError(
      body.error?.message ?? `Request failed (${response.status})`,
      response.status,
      body.error?.code,
      body.error?.request_id,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function requestAudio(path: string, init: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiError;
    throw new ApiRequestError(
      body.error?.message ?? `Request failed (${response.status})`,
      response.status,
      body.error?.code,
      body.error?.request_id,
    );
  }
  return response.blob();
}

async function requestOCR(image: Blob, language: string, cloudConsent = false): Promise<OCRResponse> {
  const form = new FormData();
  form.append("image", image, "lingua-ocr.png");
  form.append("cloud_consent", String(cloudConsent));
  const response = await fetch(`${API_BASE_URL}/api/v1/ocr/extract?language=${encodeURIComponent(language)}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiError;
    throw new ApiRequestError(body.error?.message ?? `Request failed (${response.status})`, response.status, body.error?.code, body.error?.request_id);
  }
  return response.json() as Promise<OCRResponse>;
}

export const api = {
  getLanguages: () => request<Language[]>("/api/v1/languages"),
  getCapabilities: () => request<Capabilities>("/api/v1/capabilities"),
  getSpeechCapabilities: () => request<SpeechCapabilities>("/api/v1/speech/capabilities"),
  getOcrCapabilities: () => request<OCRCapabilities>("/api/v1/ocr/capabilities"),
  extractOcr: requestOCR,
  translateText: (payload: { source_language: string | null; target_language: string; text: string }) =>
    request<TranslationResponse>("/api/v1/translations/text", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  transcribeVoice: (audio: Blob, locale: string) => request<VoiceTranscriptionResponse>(`/api/v1/voice/transcribe?locale=${encodeURIComponent(locale)}`, {
    method: "POST",
    headers: { "Content-Type": audio.type || "audio/webm" },
    body: audio,
  }),
  synthesizeVoice: (payload: { text: string; locale: string; voice: string }) => requestAudio("/api/v1/voice/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
  uploadDocument: (file: File, sourceLanguage: string | null, onProgress?: (progress: number) => void) => new Promise<DocumentJob>((resolve, reject) => {
    const form = new FormData();
    form.append("document", file, file.name);
    if (sourceLanguage) form.append("source_language", sourceLanguage);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}/api/v1/documents`);
    Object.entries(documentHeaders()).forEach(([key, value]) => xhr.setRequestHeader(key, value));
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100)); };
    xhr.onload = () => {
      const body = JSON.parse(xhr.responseText || "{}");
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as DocumentJob);
      else reject(new ApiRequestError(body.error?.message ?? `Request failed (${xhr.status})`, xhr.status, body.error?.code, body.error?.request_id));
    };
    xhr.onerror = () => reject(new ApiRequestError("Network request failed", 0));
    xhr.send(form);
  }),
  getDocument: (id: string) => request<DocumentJob>(`/api/v1/documents/${encodeURIComponent(id)}`, { headers: documentHeaders() }),
  getDocumentSegments: (id: string) => request<DocumentSegmentsResponse>(`/api/v1/documents/${encodeURIComponent(id)}/segments`, { headers: documentHeaders() }),
  updateDocumentSegments: (id: string, segments: DocumentSegment[]) => request<DocumentSegmentsResponse>(`/api/v1/documents/${encodeURIComponent(id)}/segments`, { method: "PUT", headers: documentHeaders(), body: JSON.stringify({ segments }) }),
  translateDocument: (id: string, payload: { source_language: string | null; target_language: string; reviewed: boolean }, idempotencyKey: string) => request<DocumentJob>(`/api/v1/documents/${encodeURIComponent(id)}/translate`, { method: "POST", headers: documentHeaders({ "Idempotency-Key": idempotencyKey }), body: JSON.stringify(payload) }),
  cancelDocument: (id: string) => request<DocumentJob>(`/api/v1/documents/${encodeURIComponent(id)}/cancel`, { method: "POST", headers: documentHeaders() }),
  retryDocument: (id: string) => request<DocumentJob>(`/api/v1/documents/${encodeURIComponent(id)}/retry`, { method: "POST", headers: documentHeaders() }),
  deleteDocument: (id: string) => request<void>(`/api/v1/documents/${encodeURIComponent(id)}`, { method: "DELETE", headers: documentHeaders() }),
  downloadDocument: async (id: string): Promise<{ blob: Blob; filename: string }> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${encodeURIComponent(id)}/download`, { headers: documentHeaders() });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as ApiError;
      throw new ApiRequestError(body.error?.message ?? `Request failed (${response.status})`, response.status, body.error?.code, body.error?.request_id);
    }
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? "translated-document";
    return { blob: await response.blob(), filename };
  },
};

