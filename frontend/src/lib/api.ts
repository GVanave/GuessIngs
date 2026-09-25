import type {
  Analysis, AnalysisSummary, AnalyzeInput, Comparison, Dashboard, Extraction, Page, Preferences,
  ProductBrief, SavedProduct, User, VerifyResult,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const NETWORK_MESSAGE = "We couldn't reach the server. Check your connection and try again.";

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

export async function request<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const method = (rest.method ?? "GET").toUpperCase();
  const h = new Headers(headers);
  h.set("Accept", "application/json");
  if (json !== undefined) h.set("Content-Type", "application/json");
  if (method !== "GET" && method !== "HEAD") {
    const csrf = readCookie("gi_csrf");
    if (csrf) h.set("X-CSRF-Token", csrf);
  }

  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...rest,
      method,
      headers: h,
      credentials: "same-origin",
      body: json !== undefined ? JSON.stringify(json) : rest.body,
    });
  } catch {
    throw new ApiError(0, "network_error", NETWORK_MESSAGE);
  }

  if (res.status === 204) return undefined as T;
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const err = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown> } } | null)?.error;
    const fallback =
      res.status >= 500 ? "Something went wrong on our side. Please try again." : "The request couldn't be completed.";
    throw new ApiError(res.status, err?.code ?? `http_${res.status}`, err?.message ?? fallback, err?.details);
  }
  return body as T;
}

export const api = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    request<{ user: User }>("/auth/register", { method: "POST", json: data }),
  login: (data: { email: string; password: string }) => request<{ user: User }>("/auth/login", { method: "POST", json: data }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () => request<User>("/auth/me"),
  updateMe: (data: { full_name?: string; preferences?: Preferences }) => request<User>("/users/me", { method: "PATCH", json: data }),
  changePassword: (data: { current_password: string; new_password: string }) =>
    request<{ user: User }>("/users/me/password", { method: "POST", json: data }),
  deleteAccount: (password: string) => request<void>("/users/me", { method: "DELETE", json: { password } }),

  extract: (file: Blob, filename = "label.jpg") => {
    const form = new FormData();
    form.append("file", file, filename);
    return request<Extraction>("/scan/extract", { method: "POST", body: form });
  },
  analyze: (data: AnalyzeInput) => request<Analysis>("/analyses", { method: "POST", json: data }),
  analysis: (id: string) => request<Analysis>(`/analyses/${encodeURIComponent(id)}`),
  verify: (id: string) => request<VerifyResult>(`/analyses/${encodeURIComponent(id)}/verify`),
  deleteAnalysis: (id: string) => request<void>(`/analyses/${encodeURIComponent(id)}`, { method: "DELETE" }),
  history: (params: { limit?: number; offset?: number; verdict?: string; q?: string }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && qs.set(k, String(v)));
    return request<Page<AnalysisSummary>>(`/analyses?${qs}`);
  },
  compare: (ids: string[]) => request<Comparison>(`/compare?${ids.map((i) => `ids=${encodeURIComponent(i)}`).join("&")}`),
  dashboard: () => request<Dashboard>("/dashboard"),
  saved: () => request<SavedProduct[]>("/products/saved"),
  updateProduct: (id: string, data: { is_saved?: boolean; notes?: string; name?: string }) =>
    request<ProductBrief>(`/products/${encodeURIComponent(id)}`, { method: "PATCH", json: data }),
};
