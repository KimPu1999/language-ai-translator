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

  it("uses explicit consent and selective sync endpoints", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ enabled: false, server_time: new Date().toISOString(), preferences: { locale: "en", theme: "light" } }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ enabled: true, server_time: new Date().toISOString(), preferences: { locale: "en", theme: "light" } }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ accepted_count: 1, rejected_count: 0, items: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], next_cursor: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.getSyncStatus()).resolves.toMatchObject({ enabled: false });
    await expect(api.setSyncConsent(true)).resolves.toMatchObject({ enabled: true });
    const record = { entity_type: "translation" as const, client_record_id: "web-1", client_updated_at: new Date().toISOString(), source_language: "en", target_language: "my", source_text: "Hello", translated_text: "မင်္ဂလာပါ", provider: "local" };
    await expect(api.previewSync([record])).resolves.toMatchObject({ accepted_count: 1 });
    await expect(api.importSync([record], "web-idempotency-1")).resolves.toMatchObject({ items: [] });
    expect(fetchMock).toHaveBeenNthCalledWith(3, expect.stringContaining("/api/v1/sync/preview"), expect.objectContaining({ method: "POST" }));
  });
});
