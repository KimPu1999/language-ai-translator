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

