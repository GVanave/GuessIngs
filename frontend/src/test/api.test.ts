import { api, ApiError, request } from "@/lib/api";

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "gi_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

describe("api client", () => {
  it("sends the CSRF cookie as a header on mutations only", async () => {
    document.cookie = "gi_csrf=token123";
    const fetchMock = mockFetch(201, { id: "1" });
    await api.analyze({ ingredients_text: "oats" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/analyses");
    expect(new Headers(init.headers).get("X-CSRF-Token")).toBe("token123");
    expect(JSON.parse(init.body)).toEqual({ ingredients_text: "oats" });

    mockFetch(200, {});
    await api.me();
    const [, getInit] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(new Headers(getInit.headers).get("X-CSRF-Token")).toBeNull();
  });

  it("turns API error bodies into ApiError with a friendly message", async () => {
    mockFetch(422, { error: { code: "no_ingredients", message: "We couldn't find any ingredients." } });
    const err = await request("/analyses").catch((e: ApiError) => e) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("no_ingredients");
    expect(err.message).toBe("We couldn't find any ingredients.");
    expect(err.status).toBe(422);
  });

  it("never exposes raw server errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>Traceback…</html>", { status: 502 })));
    const err = await request("/x").catch((e: ApiError) => e) as ApiError;
    expect(err.message).toBe("Something went wrong on our side. Please try again.");
  });

  it("reports network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const err = await request("/x").catch((e: ApiError) => e) as ApiError;
    expect(err.code).toBe("network_error");
    expect(err.message).toMatch(/connection/);
  });

  it("handles 204 responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    await expect(api.logout()).resolves.toBeUndefined();
  });

  it("builds compare query strings", async () => {
    const f = mockFetch(200, { items: [] });
    await api.compare(["a", "b"]);
    expect(f.mock.calls[0][0]).toBe("/api/compare?ids=a&ids=b");
  });
});
