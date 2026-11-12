import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { screen, waitFor } from "@testing-library/dom";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { api } from "./api";
import "./i18n";

vi.mock("./api", () => ({ api: { getLanguages: vi.fn(), getCapabilities: vi.fn(), translateText: vi.fn() } }));

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
    expect(await screen.findByText("Voice translation is not ready")).toBeInTheDocument();
  });
});

