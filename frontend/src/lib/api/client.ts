// Typed fetch wrapper: cookie credentials, CSRF header, single-flight 401 refresh.

const BASE = "/api/v1";

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return m ? decodeURIComponent(m[2]) : null;
}

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

interface RequestOpts {
  method?: string;
  body?: unknown;
  retry?: boolean;
}

export async function api<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const method = opts.method ?? "GET";
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") {
    const csrf = getCookie("csrf_token");
    if (csrf) headers["x-csrf-token"] = csrf;
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

  // transparent refresh on 401 (once)
  if (res.status === 401 && opts.retry !== false && !path.startsWith("/auth/")) {
    const ok = await doRefresh();
    if (ok) return api<T>(path, { ...opts, retry: false });
  }

  if (!res.ok) {
    let code = "error";
    let message = res.statusText;
    try {
      const data = await res.json();
      code = data?.error?.code ?? code;
      message = data?.error?.message ?? message;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Fetch a CSRF token (sets the csrf_token cookie) for anonymous flows. */
export async function ensureCsrf(): Promise<void> {
  if (!getCookie("csrf_token")) {
    await fetch(`${BASE}/auth/csrf`, { credentials: "include" });
  }
}
