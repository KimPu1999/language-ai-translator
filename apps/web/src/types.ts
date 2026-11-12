export type Language = {
  code: string;
  name: string;
  is_source_enabled: boolean;
  is_target_enabled: boolean;
};

export type Capabilities = {
  text_translation: boolean;
  language_detection?: boolean;
  provider_configured: boolean;
  supported_operations: string[];
};

export type TranslationResponse = {
  translated_text: string;
  provider: string;
  detected_language?: string | null;
  request_id?: string | null;
};

export type SpeechVoice = {
  name: string;
  locale: string;
  gender: string;
};

export type SpeechLanguageCapability = {
  text_code: string;
  locale: string;
  stt_enabled: boolean;
  tts_enabled: boolean;
  voices: SpeechVoice[];
};

export type SpeechCapabilities = {
  provider: string | null;
  provider_configured: boolean;
  speech_recognition: boolean;
  speech_synthesis: boolean;
  languages: SpeechLanguageCapability[];
};

export type VoiceTranscriptionResponse = {
  transcript: string;
  locale: string;
  provider: string;
  request_id: string;
};
export type OCRBlock = {
  text: string;
  left: number;
  top: number;
  width: number;
  height: number;
  confidence?: number | null;
};

export type OCRCapabilities = {
  provider: string | null;
  provider_configured: boolean;
  languages: string[];
  experimental_languages?: string[];
  consent_required?: boolean;
};

export type OCRResponse = {
  text: string;
  language: string;
  provider: string;
  blocks: OCRBlock[];
  request_id: string;
};

export type DocumentJobStatus =
  | "queued"
  | "extracting"
  | "awaiting_review"
  | "translating"
  | "exporting"
  | "completed"
  | "failed"
  | "cancelled"
  | "expired";

export type DocumentJob = {
  id: string;
  original_filename: string;
  content_type: string;
  document_format: "pdf" | "docx" | "txt";
  source_language: string | null;
  size_bytes: number;
  status: DocumentJobStatus;
  progress: number;
  page_count: number | null;
  ocr_pages: number[];
  error_code: string | null;
  error_message: string | null;
  expires_at: string;
  created_at: string;
  updated_at: string;
  target_language?: string | null;
  translation_characters?: number;
  output_content_type?: string | null;
  output_filename?: string | null;
};

export type DocumentSegment = {
  id: string;
  index: number;
  source_text: string;
  translated_text: string | null;
  kind: string;
  page: number | null;
  location: string | null;
  block_index?: number | null;
};

export type DocumentSegmentsResponse = {
  job_id: string;
  status: DocumentJobStatus;
  segments: DocumentSegment[];
};
export type ApiError = {
  error?: { code?: string; message?: string; request_id?: string };
};

export type AuthUser = {
  id: string;
  email: string;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
};

export type AuthResponse = {
  user: AuthUser;
  access_token?: string | null;
  token_type?: string | null;
  csrf_token?: string | null;
  expires_at: string;
};

export type Profile = AuthUser & { display_name: string | null };

export type UserPreferences = {
  locale: "en" | "my";
  theme: "light" | "dark" | "system";
  history_enabled: boolean;
};

export type AuthSession = {
  id: string;
  device_name: string | null;
  user_agent: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  current: boolean;
};

export type AccountHistoryItem = {
  id: string;
  source_language: string;
  target_language: string;
  source_text: string;
  translated_text: string;
  provider: string;
  created_at: string;
};

export type AccountHistoryResponse = {
  items: AccountHistoryItem[];
  total: number;
  limit: number;
  offset: number;
};

export type FavoriteItem = {
  id: string;
  translation_id: string;
  created_at: string;
  translation: AccountHistoryItem;
};

export type FavoritesResponse = {
  items: FavoriteItem[];
  total: number;
  limit: number;
  offset: number;
};

export type SyncRecordInput = {
  entity_type: "translation" | "favorite";
  client_record_id: string;
  client_updated_at: string;
  deleted?: boolean;
  source_language?: string;
  target_language?: string;
  source_text?: string;
  translated_text?: string;
  provider?: string;
  translation_client_record_id?: string;
};

export type SyncStatus = {
  enabled: boolean;
  server_time: string;
  preferences: { locale: "en" | "my"; theme: "light" | "dark" | "system" };
};
export type SyncPreviewResponse = { accepted_count: number; rejected_count: number; items: { client_record_id: string; entity_type: "translation" | "favorite"; accepted: boolean; reason?: string | null }[] };
export type SyncImportResponse = { items: { client_record_id: string; entity_type: "translation" | "favorite"; status: "applied" | "ignored" | "deleted" | "rejected"; server_record_id?: string | null; version?: number | null; error_code?: string | null }[]; next_cursor?: string | null };
export type SyncRecord = SyncRecordInput & { server_record_id?: string | null; version: number; updated_at: string; deleted: boolean };
export type SyncChangesResponse = { items: SyncRecord[]; next_cursor?: string | null; has_more: boolean };

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly requestId?: string;

  constructor(message: string, status: number, code?: string, requestId?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

