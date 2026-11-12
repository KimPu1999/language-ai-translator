import { ApiRequestError } from "./types";
import type { ApiError, Capabilities, Language, OCRCapabilities, OCRResponse, SpeechCapabilities, TranslationResponse, VoiceTranscriptionResponse } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

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
};

