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
});
