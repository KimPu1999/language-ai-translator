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

