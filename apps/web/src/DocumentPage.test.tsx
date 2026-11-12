import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DocumentPage from "./DocumentPage";
import { api } from "./api";
import "./i18n";

vi.mock("./api", () => ({
  api: {
    getLanguages: vi.fn(),
    uploadDocument: vi.fn(),
    getDocument: vi.fn(),
    getDocumentSegments: vi.fn(),
    updateDocumentSegments: vi.fn(),
    translateDocument: vi.fn(),
    cancelDocument: vi.fn(),
    retryDocument: vi.fn(),
    deleteDocument: vi.fn(),
    downloadDocument: vi.fn(),
  },
}));

const job = {
  id: "job-1",
  original_filename: "greeting.txt",
  content_type: "text/plain",
  document_format: "txt" as const,
  source_language: null,
  size_bytes: 7,
  status: "awaiting_review" as const,
  progress: 100,
  page_count: 1,
  ocr_pages: [],
  error_code: null,
  error_message: null,
  expires_at: "2099-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const segment = { id: "segment-0-0", index: 0, source_text: "Hello", translated_text: null, kind: "paragraph", page: null, location: null };

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><DocumentPage /></QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getLanguages).mockResolvedValue([
    { code: "en", name: "English", is_source_enabled: true, is_target_enabled: true },
    { code: "my", name: "Burmese", is_source_enabled: true, is_target_enabled: true },
  ]);
  vi.mocked(api.getDocument).mockResolvedValue(job);
  vi.mocked(api.getDocumentSegments).mockResolvedValue({ job_id: "job-1", status: "awaiting_review", segments: [segment] });
  vi.mocked(api.updateDocumentSegments).mockImplementation(async (_id, segments) => ({ job_id: "job-1", status: "awaiting_review", segments }));
  vi.mocked(api.translateDocument).mockResolvedValue({ ...job, status: "translating", progress: 1, target_language: "my" });
});

describe("Phase 5D document translator", () => {
  it("rejects unsupported files before upload", async () => {
    const user = userEvent.setup();
    renderPage();
    const input = screen.getByLabelText(/choose document/i);
    await user.upload(input, new File(["not a PDF"], "malware.pdf", { type: "application/pdf" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The PDF signature is invalid");
    expect(api.uploadDocument).not.toHaveBeenCalled();
  });

  it("uploads, exposes editable review, and sends explicit confirmation to translation", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadDocument).mockImplementation(async (_file, _source, onProgress) => { onProgress?.(100); return job; });
    renderPage();
    await user.upload(screen.getByLabelText(/choose document/i), new File(["Hello"], "greeting.txt", { type: "text/plain" }));
    await user.click(await screen.findByRole("button", { name: "Upload document" }));
    expect(await screen.findByText("Review extracted text")).toBeInTheDocument();
    const editor = await screen.findByRole("textbox", { name: /Original 1/i });
    await user.clear(editor);
    await user.type(editor, "မင်္ဂလာပါ");
    await user.click(screen.getByRole("button", { name: "Save review" }));
    await waitFor(() => expect(api.updateDocumentSegments).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "Translate document" }));
    await waitFor(() => expect(api.translateDocument).toHaveBeenCalledWith("job-1", expect.objectContaining({ reviewed: true, target_language: "my" }), expect.any(String)));
  });
});
