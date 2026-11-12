import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CameraPage from "./CameraPage";
import { api } from "./api";
import "./i18n";

vi.mock("./api", () => ({ api: { getLanguages: vi.fn(), getOcrCapabilities: vi.fn(), extractOcr: vi.fn(), translateText: vi.fn() } }));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><CameraPage /></QueryClientProvider>);
}

beforeEach(() => {
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:camera-test") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  vi.mocked(api.getOcrCapabilities).mockResolvedValue({ provider: "fake-ocr", provider_configured: true, languages: ["en", "my"] });
  vi.mocked(api.getLanguages).mockResolvedValue([
    { code: "en", name: "English", is_source_enabled: true, is_target_enabled: true },
    { code: "my", name: "Burmese", is_source_enabled: true, is_target_enabled: true },
  ]);
  vi.mocked(api.extractOcr).mockResolvedValue({ text: "မင်္ဂလာပါ", language: "my", provider: "fake-ocr", request_id: "ocr-1", blocks: [{ text: "မင်္ဂလာပါ", left: 0, top: 0, width: 0.5, height: 0.2, confidence: 98 }] });
  vi.mocked(api.translateText).mockResolvedValue({ translated_text: "Hello", provider: "fake-translation" });
  class FakeImage {
    naturalWidth = 100;
    naturalHeight = 80;
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    set src(_value: string) { queueMicrotask(() => this.onload?.()); }
  }
  vi.stubGlobal("Image", FakeImage);
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ translate: vi.fn(), rotate: vi.fn(), drawImage: vi.fn() } as unknown as CanvasRenderingContext2D);
  vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation((callback) => callback(new Blob(["image"], { type: "image/png" })));
});

describe("CameraPage", () => {
  it("scans an uploaded image, supports review, and translates only after confirmation", async () => {
    const user = userEvent.setup();
    renderPage();
    const input = document.querySelector('input[type="file"]');
    expect(input).toBeTruthy();
    await user.upload(input as HTMLInputElement, new File(["image"], "sample.png", { type: "image/png" }));
    await user.click(screen.getByRole("button", { name: "Scan text" }));
    expect(await screen.findByDisplayValue("မင်္ဂလာပါ")).toBeInTheDocument();
    expect(api.extractOcr).toHaveBeenCalledWith(expect.any(Blob), "en", false);
    const editor = screen.getByRole("textbox", { name: "Extracted text" });
    await user.clear(editor);
    await user.type(editor, "မင်္ဂလာပါ Hello");
    await user.click(screen.getByRole("button", { name: "Translate reviewed text" }));
    expect(await screen.findByText("Hello")).toBeInTheDocument();
    expect(api.translateText).toHaveBeenCalledWith({ source_language: "en", target_language: "my", text: "မင်္ဂလာပါ Hello" });
  });

  it("shows OCR provider errors without pretending to scan", async () => {
    vi.mocked(api.getOcrCapabilities).mockResolvedValue({ provider: null, provider_configured: false, languages: [] });
    renderPage();
    expect(await screen.findByText("OCR is not configured on the API. No image was uploaded.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scan text" })).toBeDisabled();
  });
});
