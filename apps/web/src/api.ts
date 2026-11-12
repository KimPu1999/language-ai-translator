import { ApiRequestError } from "./types";
import type { ApiError, Capabilities, Language, TranslationResponse } from "./types";

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

export const api = {
  getLanguages: () => request<Language[]>("/api/v1/languages"),
  getCapabilities: () => request<Capabilities>("/api/v1/capabilities"),
  translateText: (payload: { source_language: string | null; target_language: string; text: string }) =>
    request<TranslationResponse>("/api/v1/translations/text", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

