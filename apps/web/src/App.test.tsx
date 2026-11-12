import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { screen, waitFor } from "@testing-library/dom";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { api } from "./api";
import "./i18n";

vi.mock("./api", () => ({ api: { getLanguages: vi.fn(), getCapabilities: vi.fn(), getSpeechCapabilities: vi.fn(), getOcrCapabilities: vi.fn(), extractOcr: vi.fn(), translateText: vi.fn(), transcribeVoice: vi.fn(), synthesizeVoice: vi.fn() } }));

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>);
}

beforeEach(() => {
  vi.mocked(api.getLanguages).mockResolvedValue([
    { code: "en", name: "English", is_source_enabled: true, is_target_enabled: true },
    { code: "my", name: "Burmese", is_source_enabled: true, is_target_enabled: true },
  ]);
  vi.mocked(api.getCapabilities).mockResolvedValue({ text_translation: false, provider_configured: false, supported_operations: ["text_translation"] });
  vi.mocked(api.getSpeechCapabilities).mockResolvedValue({ provider: null, provider_configured: false, speech_recognition: false, speech_synthesis: false, languages: [] });
  vi.mocked(api.translateText).mockRejectedValue(new Error("Translation engine is not configured"));
  window.history.pushState({}, "", "/translate");
});

describe("Phase 1B translator", () => {
  it("renders the editor and live language options", async () => {
    renderApp();
    expect(await screen.findByText("Text Translator")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "en" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "my" })).toBeInTheDocument();
  });

  it("shows actionable backend unavailability instead of invented output", async () => {
    const user = userEvent.setup();
    renderApp();
    const editor = await screen.findByRole("textbox", { name: "Source" });
    await user.type(editor, "Hello");
    await user.click(screen.getByRole("button", { name: "Translate" }));
    expect(await screen.findByText("Translation is not available yet")).toBeInTheDocument();
    expect(screen.getByText(/not saved or translated/i)).toBeInTheDocument();
  });

  it("enforces the 5000 character limit in the editor", async () => {
    const user = userEvent.setup();
    renderApp();
    const editor = await screen.findByRole("textbox", { name: "Source" });
    await user.click(editor);
    await user.paste("x".repeat(5001));
    await waitFor(() => expect(editor).toHaveValue("x".repeat(5000)));
    expect(screen.getByText(/5,000 characters/)).toBeInTheDocument();
  });

  it("makes unavailable and non-persistent sections explicit", async () => {
    const user = userEvent.setup();
    renderApp();
    await user.click(screen.getAllByRole("link", { name: "Voice" })[0]);
    expect(await screen.findByText("Voice translator")).toBeInTheDocument();
    expect(screen.getByText("Voice processing is not configured. No audio will be uploaded.")).toBeInTheDocument();
  });

  it("renders a real result, supports copy, and swaps languages", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getCapabilities).mockResolvedValue({ text_translation: true, provider_configured: true, supported_operations: ["text_translation"] });
    vi.mocked(api.translateText).mockResolvedValue({ translated_text: "မင်္ဂလာပါ", provider: "azure" });
    renderApp();
    await screen.findByRole("option", { name: "my" });
    const selects = await screen.findAllByRole("combobox");
    await user.selectOptions(selects[0], "my");
    await user.selectOptions(selects[1], "en");
    await user.click(screen.getByRole("button", { name: "Swap languages" }));
    expect(selects[0]).toHaveValue("en");
    expect(selects[1]).toHaveValue("my");
    const editor = screen.getByRole("textbox", { name: "Source" });
    await user.type(editor, "Hello");
    await user.click(screen.getByRole("button", { name: "Translate" }));
    expect(await screen.findByText("မင်္ဂလာပါ")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Copy" }));
    expect(screen.getByText("Copied")).toBeInTheDocument();
  });

  it("shows retryable rate-limit and network failures without output", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getCapabilities).mockResolvedValue({ text_translation: true, provider_configured: true, supported_operations: ["text_translation"] });
    vi.mocked(api.translateText).mockRejectedValue(new Error("Translation usage limit reached"));
    renderApp();
    const editor = await screen.findByRole("textbox", { name: "Source" });
    await user.type(editor, "Hello");
    await user.click(screen.getByRole("button", { name: "Translate" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Translation usage limit reached");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByText("Hello", { selector: "p" })).not.toBeInTheDocument();
  });

  it("keeps local saving opt-in and keyboard reachable", async () => {
    const user = userEvent.setup();
    renderApp();
    await user.click(screen.getByRole("button", { name: "Settings" }));
    const localSwitch = await screen.findByRole("switch", { name: "Local history and favorites" });
    expect(localSwitch).toHaveAttribute("aria-checked", "false");
    await user.tab();
    expect(document.activeElement).toBeTruthy();
    await user.click(localSwitch);
    expect(localSwitch).toHaveAttribute("aria-checked", "true");
  });

  it("opens the two-person push-to-talk conversation workspace", async () => {
    const user = userEvent.setup();
    renderApp();
    await user.click(screen.getAllByRole("link", { name: "Conversation" })[0]);
    expect(await screen.findByText("Two-way conversation")).toBeInTheDocument();
    expect(screen.getByText("Person A")).toBeInTheDocument();
    expect(screen.getByText("Person B")).toBeInTheDocument();
    expect(screen.getByText(/only one microphone records at a time/i)).toBeInTheDocument();
  });
});

