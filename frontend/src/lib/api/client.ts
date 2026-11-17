const backendOrigin = (process.env.NEXT_PUBLIC_BACKEND_API_URL || "").replace(
  /\/$/,
  ""
);

export const API_BASE_URL = `${backendOrigin}/api/v1`;

export const AUTH_EXPIRED_EVENT = "auth:expired";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

export interface ApiError {
  message: string;
  status: number;
  code?: string;
}

/**
 * Narrow an unknown thrown value to the error shape produced by this client.
 *
 * @param value - Any caught value.
 * @returns True when the value carries a message and an HTTP status.
 */
export function isApiError(value: unknown): value is ApiError {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<ApiError>;
  return (
    typeof candidate.message === "string" && typeof candidate.status === "number"
  );
}

/**
 * Extract a user-facing message from any caught value.
 *
 * @param error - Value caught from a failed request or browser API.
 * @param fallback - Message used when the value carries no text.
 * @returns The backend message for ApiError, the message of other errors, or the fallback.
 */
export function getErrorMessage(error: unknown, fallback: string): string {
  if (isApiError(error) && error.message) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

const NETWORK_ERROR: ApiError = {
  message: "Không thể kết nối máy chủ",
  status: 0,
  code: "network_error",
};

interface ErrorPayload {
  error?: { code?: string; message?: string };
  detail?: string | Array<{ msg?: string }>;
  message?: string;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

let shareToken: string | null = null;
let refreshInFlight: Promise<boolean> | null = null;

const MEETING_SCOPED_PATH =
  /^\/(meetings\/[0-9a-f-]{36}|transcripts|summaries|chat|exports|audio)(\/|\?|$)/i;

/**
 * Remember the share-link token of the meeting being viewed.
 *
 * The token is appended to every meeting-scoped request so guests can read
 * sub-resources (transcript, summary, chat, exports).
 *
 * @param token - Share token from the URL, or null to clear it.
 */
export function setShareToken(token: string | null): void {
  shareToken = token;
}

/**
 * Build an absolute or same-origin backend URL.
 *
 * @param path - Backend path beginning with `/api` or `/`.
 * @returns URL suitable for browser fetch or media elements.
 */
export function buildBackendUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${backendOrigin}${normalizedPath}`;
}

/**
 * Persist a token pair issued by the backend.
 *
 * @param tokens - Access and refresh tokens.
 */
export function storeTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

/** Remove stored tokens. */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

function withShareToken(path: string): string {
  if (!shareToken || !MEETING_SCOPED_PATH.test(path) || /[?&]share=/.test(path)) {
    return path;
  }
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}share=${encodeURIComponent(shareToken)}`;
}

/**
 * Exchange the refresh token for a new pair, shared by all concurrent callers.
 *
 * Refresh tokens are single use, so parallel refreshes would trip the backend
 * reuse detection and sign the user out.
 *
 * @returns True when new tokens were stored.
 */
function refreshAccessToken(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (!refreshToken) return false;
      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) return false;
        storeTokens((await response.json()) as TokenPair);
        return true;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function buildError(response: Response): Promise<ApiError> {
  let message = `Lỗi yêu cầu: ${response.statusText}`;
  let code: string | undefined;
  try {
    const data = (await response.json()) as ErrorPayload;
    if (data.error?.message) {
      message = data.error.message;
      code = data.error.code;
    } else if (typeof data.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail.map((item) => item.msg).filter(Boolean).join("; ");
    } else if (data.message) {
      message = data.message;
    }
  } catch {
    // Body was not JSON, keep the status text
  }
  return { message, status: response.status, code };
}

/**
 * Fetch with the Bearer token, refreshing it once on a 401 and retrying.
 *
 * @param path - Endpoint path starting with /
 * @param options - Fetch request options
 * @returns The final HTTP response
 */
async function authorizedFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${withShareToken(path.startsWith("/") ? path : `/${path}`)}`;

  const send = (): Promise<Response> => {
    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem(ACCESS_TOKEN_KEY)
        : null;
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return fetch(url, { ...options, headers }).catch(() => {
      throw { ...NETWORK_ERROR } satisfies ApiError;
    });
  };

  const response = await send();
  const isAuthRoute = path.startsWith("/auth/");
  if (response.status !== 401 || isAuthRoute || typeof window === "undefined") {
    return response;
  }
  if (!localStorage.getItem(ACCESS_TOKEN_KEY)) {
    return response;
  }

  if (await refreshAccessToken()) {
    return send();
  }
  clearTokens();
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  return response;
}

/**
 * Open a streaming response (Server-Sent Events) with the same auth, refresh and
 * share-token handling as ordinary requests.
 *
 * @param path - Endpoint path starting with /
 * @param options - Fetch request options, including an AbortSignal
 * @returns The response, ready to read its body incrementally
 * @throws ApiError when the server refuses before streaming starts
 */
export async function fetchStream(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const response = await authorizedFetch(path, options);
  if (!response.ok) {
    throw await buildError(response);
  }
  return response;
}

/**
 * Perform an authenticated HTTP request against the Backend API.
 *
 * @param path - Endpoint path starting with /
 * @param options - Fetch request options
 * @returns Parsed JSON response
 * @throws ApiError with the backend error code and message
 */
export async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await authorizedFetch(path, options);

  if (!response.ok) {
    throw await buildError(response);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * Trigger file download directly from backend API.
 *
 * @param path - Download endpoint path
 * @param fallbackFilename - Default file name if not provided by header
 */
export async function downloadFile(
  path: string,
  fallbackFilename: string
): Promise<void> {
  const response = await authorizedFetch(path);

  if (!response.ok) {
    throw await buildError(response);
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;

  const disposition = response.headers.get("Content-Disposition");
  let filename = fallbackFilename;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
}
