/** Error shape we support (axios-like + fetch throw with response). */
interface ErrLike {
  response?: { status?: number; data?: ApiErrorData };
  message?: string;
}

/** Backend can return detail as { code, message } or (legacy) array of validation errors. */
interface ApiErrorData {
  message?: string;
  detail?: { code?: string; message?: string } | Array<{ msg?: string; loc?: unknown }>;
}

/** Error codes that indicate input/validation issues (show inline or near input). */
const VALIDATION_ERROR_CODES = new Set([
  "message_required",
  "message_too_long",
  "history_too_long",
  "invalid_request",
]);

function getDetailMessage(data: ApiErrorData | undefined): string | null {
  if (!data) return null;
  const detail = data.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail) && typeof detail.message === "string")
    return detail.message;
  if (data.message && typeof data.message === "string") return data.message;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return null;
}

/**
 * Derives a user-facing message when both stream and non-stream chat requests fail.
 */
export function getChatErrorMessage(streamErr: unknown, chatErr: unknown): string {
  const err = chatErr ?? streamErr;
  const message = (err as Error)?.message ?? "";
  const isNetworkError = /fetch|network|failed to fetch|abort/i.test(message);

  if (err && typeof err === "object") {
    const e = err as ErrLike;
    if (e.response) {
      const msg = getDetailMessage(e.response.data);
      if (msg) return msg;
      if (e.response.status === 502 || e.response.status === 503)
        return "服务暂时不可用，请稍后重试。";
      if (e.response.status === 404)
        return "助手接口未找到（/api/ai/chat）。请确认连接的是 Waifu Tutor 后端，并检查后端端口配置。";
      if (e.response.status)
        return `请求失败 (${e.response.status})，请稍后重试。`;
    }
  }

  if (isNetworkError)
    return "无法连接助手服务。请确认后端已启动（默认端口 8000）。";
  return "Failed to get response from assistant.";
}

/**
 * Whether the error is due to invalid input (validation). Use this to show the error
 * near the input or with a softer style; otherwise treat as server/network error.
 */
export function getChatErrorKind(streamErr: unknown, chatErr: unknown): "validation" | "server" {
  const err = chatErr ?? streamErr;
  if (err && typeof err === "object") {
    const e = err as ErrLike;
    const code = e.response?.data?.detail && typeof e.response.data.detail === "object" && !Array.isArray(e.response.data.detail)
      ? (e.response.data.detail as { code?: string }).code
      : undefined;
    if (code && VALIDATION_ERROR_CODES.has(code)) return "validation";
    if (e.response?.status === 400) return "validation";
  }
  return "server";
}
