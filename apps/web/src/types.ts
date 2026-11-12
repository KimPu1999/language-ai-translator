export type Language = {
  code: string;
  name: string;
  is_source_enabled: boolean;
  is_target_enabled: boolean;
};

export type Capabilities = {
  text_translation: boolean;
  provider_configured: boolean;
  supported_operations: string[];
};

export type TranslationResponse = { translated_text: string; provider: string };
export type ApiError = { error?: { code?: string; message?: string } };

