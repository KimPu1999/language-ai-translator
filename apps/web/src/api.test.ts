import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("typed API client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("parses a translation response without exposing provider configuration", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ translated_text: "hello", provider: "azure" }), { status: 200 })));
    await expect(api.translateText({ source_language: "my", target_language: "en", text: "မင်္ဂလာပါ" })).resolves.toMatchObject({ translated_text: "hello", provider: "azure" });
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/translations/text"), expect.objectContaining({ method: "POST" }));
  });

  it("preserves structured rate-limit and timeout status information", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "RATE_LIMIT_EXCEEDED", message: "Translation usage limit reached", request_id: "req-1" } }), { status: 429 })));
    await expect(api.translateText({ source_language: null, target_language: "en", text: "hello" })).rejects.toMatchObject({ status: 429, code: "RATE_LIMIT_EXCEEDED", requestId: "req-1" });
  });

  it("sends recorded audio to the backend and returns synthesized audio", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ transcript: "မင်္ဂလာပါ", locale: "my-MM", provider: "azure", request_id: "req-2" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(new Blob(["RIFF"], { type: "audio/wav" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const recording = new Blob(["audio"], { type: "audio/webm" });
    await expect(api.transcribeVoice(recording, "my-MM")).resolves.toMatchObject({ transcript: "မင်္ဂလာပါ", locale: "my-MM" });
    await expect(api.synthesizeVoice({ text: "မင်္ဂလာပါ", locale: "my-MM", voice: "my-MM-NilarNeural" })).resolves.toMatchObject({ size: 13 });
    expect(fetchMock).toHaveBeenNthCalledWith(1, expect.stringContaining("/api/v1/voice/transcribe?locale=my-MM"), expect.objectContaining({ method: "POST", body: recording, headers: { "Content-Type": "audio/webm" } }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, expect.stringContaining("/api/v1/voice/synthesize"), expect.objectContaining({ method: "POST" }));
  });
});
