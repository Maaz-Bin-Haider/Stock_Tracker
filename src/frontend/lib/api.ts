export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed (${status})`;
    super(detail);
    this.status = status;
    this.body = body;
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export async function api<T = unknown>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = getCookie("csrftoken");
    if (token) headers["X-CSRFToken"] = token;
  }

  const response = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 204) return undefined as T;
  const isJson = response.headers.get("content-type")?.includes("json");
  const body = isJson ? await response.json() : await response.text();
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}

/** POST multipart form data (file uploads); same session/CSRF handling as api(). */
export async function apiUpload<T = unknown>(path: string, form: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getCookie("csrftoken");
  if (token) headers["X-CSRFToken"] = token;
  const response = await fetch(path, {
    method: "POST",
    headers,
    credentials: "same-origin",
    body: form,
  });
  const isJson = response.headers.get("content-type")?.includes("json");
  const body = isJson ? await response.json() : await response.text();
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}

/** Flatten a DRF error body ({field: [messages]} or {detail: msg}) to one line. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError && typeof err.body === "object" && err.body !== null) {
    return Object.entries(err.body as Record<string, unknown>)
      .map(([key, value]) => {
        const text = Array.isArray(value) ? value.join(" ") : String(value);
        return key === "detail" || key === "non_field_errors" ? text : `${key}: ${text}`;
      })
      .join(" · ");
  }
  return err instanceof Error ? err.message : "Something went wrong.";
}
