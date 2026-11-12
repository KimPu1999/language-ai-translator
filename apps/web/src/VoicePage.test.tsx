import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VoicePage from "./VoicePage";
import { api } from "./api";
import i18n from "./i18n";

vi.mock("./api", () => ({
  api: {
    getLanguages: vi.fn(),
    getSpeechCapabilities: vi.fn(),
    translateText: vi.fn(),
    transcribeVoice: vi.fn(),
    synthesizeVoice: vi.fn(),
  },
}));

class FakeMediaRecorder {
  static isTypeSupported = vi.fn(() => true);
  state: "inactive" | "recording" = "inactive";
  mimeType = "audio/webm";
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(_stream: MediaStream, _options: MediaRecorderOptions) {}

  start() { this.state = "recording"; }

  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["audio"], { type: this.mimeType }) });
    this.onstop?.();
  }
}

function renderVoice() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><VoicePage /></QueryClientProvider>);
}

beforeEach(() => {
  void i18n.changeLanguage("en");
  vi.clearAllMocks();
  vi.mocked(api.getLanguages).mockResolvedValue([
    { code: "en", name: "English", is_source_enabled: true, is_target_enabled: true },
    { code: "my", name: "Burmese", is_source_enabled: true, is_target_enabled: true },
  ]);
  vi.mocked(api.getSpeechCapabilities).mockResolvedValue({
    provider: "azure",
    provider_configured: true,
    speech_recognition: true,
    speech_synthesis: true,
    languages: [
      { text_code: "en", locale: "en-US", stt_enabled: true, tts_enabled: true, voices: [{ name: "en-US-JennyNeural", locale: "en-US", gender: "Female" }] },
      { text_code: "my", locale: "my-MM", stt_enabled: true, tts_enabled: true, voices: [{ name: "my-MM-NilarNeural", locale: "my-MM", gender: "Female" }] },
    ],
  });
  vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] }) },
  });
});

describe("VoicePage", () => {
  it("shows a clear microphone permission error", async () => {
    const user = userEvent.setup();
    vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValue(new DOMException("Denied", "NotAllowedError"));
    renderVoice();
    await user.click(await screen.findByRole("button", { name: "Start recording" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Microphone permission was denied");
  });

  it("records, uploads audio, and keeps Burmese transcript editable", async () => {
    const user = userEvent.setup();
    vi.mocked(api.transcribeVoice).mockResolvedValue({ transcript: "မင်္ဂလာပါ", locale: "my-MM", provider: "azure", request_id: "req-1" });
    renderVoice();
    await user.click(await screen.findByRole("button", { name: "Start recording" }));
    await user.click(screen.getByRole("button", { name: "Stop recording" }));
    expect(api.transcribeVoice).toHaveBeenCalledWith(expect.any(Blob), "en-US");
    expect(await screen.findByDisplayValue("မင်္ဂလာပါ")).toBeInTheDocument();
    const editor = screen.getByRole("textbox", { name: "Transcript" });
    await user.clear(editor);
    await user.type(editor, "မင်္ဂလာပါ၊ Lingua");
    expect(editor).toHaveValue("မင်္ဂလာပါ၊ Lingua");
  });

  it("translates the edited transcript and generates playable audio", async () => {
    const user = userEvent.setup();
    vi.mocked(api.transcribeVoice).mockResolvedValue({ transcript: "မင်္ဂလာပါ", locale: "my-MM", provider: "azure", request_id: "req-2" });
    vi.mocked(api.translateText).mockResolvedValue({ translated_text: "Hello", provider: "azure" });
    vi.mocked(api.synthesizeVoice).mockResolvedValue(new Blob(["RIFF"], { type: "audio/wav" }));
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:test"), revokeObjectURL: vi.fn() });
    renderVoice();
    await user.click(await screen.findByRole("button", { name: "Start recording" }));
    await user.click(screen.getByRole("button", { name: "Stop recording" }));
    await screen.findByDisplayValue("မင်္ဂလာပါ");
    await user.click(screen.getByRole("button", { name: "Translate" }));
    expect(api.translateText).toHaveBeenCalledWith({ source_language: "en", target_language: "my", text: "မင်္ဂလာပါ" });
    expect(await screen.findByText("Hello")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate audio" }));
    expect(api.synthesizeVoice).toHaveBeenCalledWith({ text: "Hello", locale: "my-MM", voice: "my-MM-NilarNeural" });
    expect(await screen.findByText("Audio ready")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Play audio" })).toBeInTheDocument());
  });
});
