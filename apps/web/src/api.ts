import { ApiRequestError } from "./types";
import type { AccountHistoryResponse, ApiError, AuthResponse, AuthSession, Capabilities, DocumentJob, DocumentSegment, DocumentSegmentsResponse, FavoriteItem, FavoritesResponse, Language, OCRCapabilities, OCRResponse, Profile, SpeechCapabilities, TranslationResponse, UserPreferences, VoiceTranscriptionResponse, AuthUser, SyncChangesResponse, SyncImportResponse, SyncPreviewResponse, SyncRecordInput, SyncStatus } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const documentCapabilityToken = import.meta.env.VITE_DOCUMENT_CAPABILITY_TOKEN as string | undefined;
const csrfCookieName = (import.meta.env.VITE_AUTH_CSRF_COOKIE_NAME as string | undefined) ?? "lingua_csrf";

function readCookie(name: string): string | null {
  const encodedName = encodeURIComponent(name);
  const entry = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${encodedName}=`));
  return entry ? decodeURIComponent(entry.slice(encodedName.length + 1)) : null;
}

function isUnsafe(method?: string): boolean {
  if (!method) return false;
  return !["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
}

function isPublicAuthPath(path: string): boolean {
  return ["/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/verify-email", "/api/v1/auth/resend-verification", "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password"].some((publicPath) => path.startsWith(publicPath));
}

function notifySessionExpiry(path: string, status: number): void {
  // The bootstrap /me request is expected to return 401 for a signed-out
  // visitor. It must not turn the public translator into an auth redirect.
  if (status === 401 && path !== "/api/v1/auth/me" && !isPublicAuthPath(path)) window.dispatchEvent(new CustomEvent("lingua:auth-expired"));
}

function documentHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const csrf = readCookie(csrfCookieName);
  return {
    ...(documentCapabilityToken ? { "X-Document-Capability-Token": documentCapabilityToken } : {}),
    ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    ...extra,
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...((init?.headers ?? {}) as Record<string, string>) };
  if (!Object.keys(headers).some((key) => key.toLowerCase() === "content-type")) headers["Content-Type"] = "application/json";
  if (isUnsafe(init?.method) && !isPublicAuthPath(path)) {
    const csrf = readCookie(csrfCookieName);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    notifySessionExpiry(path, response.status);
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
  const headers: Record<string, string> = { ...((init.headers ?? {}) as Record<string, string>) };
  if (isUnsafe(init.method) && !isPublicAuthPath(path)) {
    const csrf = readCookie(csrfCookieName);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, credentials: "include", headers });
  if (!response.ok) {
    notifySessionExpiry(path, response.status);
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
  const csrf = readCookie(csrfCookieName);
  const response = await fetch(`${API_BASE_URL}/api/v1/ocr/extract?language=${encodeURIComponent(language)}`, {
    method: "POST",
    credentials: "include",
    headers: csrf ? { "X-CSRF-Token": csrf } : undefined,
    body: form,
  });
  if (!response.ok) {
    notifySessionExpiry("/api/v1/ocr/extract", response.status);
    const body = (await response.json().catch(() => ({}))) as ApiError;
    throw new ApiRequestError(body.error?.message ?? `Request failed (${response.status})`, response.status, body.error?.code, body.error?.request_id);
  }
  return response.json() as Promise<OCRResponse>;
}

export const api = {
  register: (payload: { email: string; password: string }) => request<{ user: AuthUser; message: string }>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ ...payload, client: "web" }) }),
  login: (payload: { email: string; password: string }) => request<AuthResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ ...payload, client: "web" }) }),
  getCurrentUser: () => request<AuthUser>("/api/v1/auth/me"),
  logout: () => request<{ message: string }>("/api/v1/auth/logout", { method: "POST" }),
  verifyEmail: (token: string) => request<{ message: string }>("/api/v1/auth/verify-email", { method: "POST", body: JSON.stringify({ token }) }),
  resendVerification: (email: string) => request<{ message: string }>("/api/v1/auth/resend-verification", { method: "POST", body: JSON.stringify({ email }) }),
  forgotPassword: (email: string) => request<{ message: string }>("/api/v1/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }),
  resetPassword: (token: string, password: string) => request<{ message: string }>("/api/v1/auth/reset-password", { method: "POST", body: JSON.stringify({ token, password }) }),
  getSessions: () => request<AuthSession[]>("/api/v1/auth/sessions"),
  revokeSession: (id: string) => request<{ message: string }>(`/api/v1/auth/sessions/${encodeURIComponent(id)}`, { method: "DELETE" }),
  getProfile: () => request<Profile>("/api/v1/profile"),
  updateProfile: (payload: { display_name: string | null }) => request<Profile>("/api/v1/profile", { method: "PATCH", body: JSON.stringify(payload) }),
  getPreferences: () => request<UserPreferences>("/api/v1/preferences"),
  updatePreferences: (payload: Partial<UserPreferences>) => request<UserPreferences>("/api/v1/preferences", { method: "PATCH", body: JSON.stringify(payload) }),
  getHistory: (params: { limit: number; offset: number; source_language?: string; target_language?: string; q?: string }) => {
    const query = new URLSearchParams({ limit: String(params.limit), offset: String(params.offset) });
    if (params.source_language) query.set("source_language", params.source_language);
    if (params.target_language) query.set("target_language", params.target_language);
    if (params.q) query.set("q", params.q);
    return request<AccountHistoryResponse>(`/api/v1/history?${query.toString()}`);
  },
  saveHistory: (payload: { source_language: string; target_language: string; source_text: string; translated_text: string; provider: string }) => request<AccountHistoryResponse["items"][number]>("/api/v1/history", { method: "POST", body: JSON.stringify(payload) }),
  deleteHistory: (id: string) => request<void>(`/api/v1/history/${encodeURIComponent(id)}`, { method: "DELETE" }),
  clearHistory: () => request<void>("/api/v1/history", { method: "DELETE" }),
  getFavorites: (params: { limit: number; offset: number }) => request<FavoritesResponse>(`/api/v1/favorites?limit=${params.limit}&offset=${params.offset}`),
  createFavorite: (translationId: string) => request<FavoriteItem>("/api/v1/favorites", { method: "POST", body: JSON.stringify({ translation_id: translationId }) }),
  deleteFavorite: (id: string) => request<void>(`/api/v1/favorites/${encodeURIComponent(id)}`, { method: "DELETE" }),
  exportAccount: async (): Promise<Blob> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/account/export`, { credentials: "include", headers: { "X-CSRF-Token": readCookie(csrfCookieName) ?? "" } });
    if (!response.ok) { notifySessionExpiry("/api/v1/account/export", response.status); const body = (await response.json().catch(() => ({}))) as ApiError; throw new ApiRequestError(body.error?.message ?? `Request failed (${response.status})`, response.status, body.error?.code, body.error?.request_id); }
    return response.blob();
  },
  deleteAccount: (password: string) => request<{ message: string }>("/api/v1/account", { method: "DELETE", body: JSON.stringify({ password }) }),
  getSyncStatus: () => request<SyncStatus>("/api/v1/sync/status"),
  setSyncConsent: (enabled: boolean) => request<SyncStatus>("/api/v1/sync/consent", { method: "PATCH", body: JSON.stringify({ enabled }) }),
  updateSyncPreferences: (payload: { locale?: "en" | "my"; theme?: "light" | "dark" | "system" }) => request<SyncStatus>("/api/v1/sync/preferences", { method: "PATCH", body: JSON.stringify(payload) }),
  previewSync: (records: SyncRecordInput[]) => request<SyncPreviewResponse>("/api/v1/sync/preview", { method: "POST", body: JSON.stringify({ records }) }),
  importSync: (records: SyncRecordInput[], idempotencyKey: string) => request<SyncImportResponse>("/api/v1/sync/import", { method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify({ records, idempotency_key: idempotencyKey }) }),
  getSyncChanges: (cursor?: string) => request<SyncChangesResponse>(`/api/v1/sync/changes?limit=50${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`),
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
    xhr.withCredentials = true;
    Object.entries(documentHeaders()).forEach(([key, value]) => xhr.setRequestHeader(key, value));
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100)); };
    xhr.onload = () => {
      const body = JSON.parse(xhr.responseText || "{}");
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as DocumentJob);
      else { if (xhr.status === 401) window.dispatchEvent(new CustomEvent("lingua:auth-expired")); reject(new ApiRequestError(body.error?.message ?? `Request failed (${xhr.status})`, xhr.status, body.error?.code, body.error?.request_id)); }
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
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/${encodeURIComponent(id)}/download`, { credentials: "include", headers: documentHeaders() });
    if (!response.ok) {
      notifySessionExpiry(`/api/v1/documents/${encodeURIComponent(id)}/download`, response.status);
      const body = (await response.json().catch(() => ({}))) as ApiError;
      throw new ApiRequestError(body.error?.message ?? `Request failed (${response.status})`, response.status, body.error?.code, body.error?.request_id);
    }
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? "translated-document";
    return { blob: await response.blob(), filename };
  },
};

