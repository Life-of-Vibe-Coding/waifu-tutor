/** Error shape we support (axios-like + generic Error). */
interface ErrLike {
  response?: { status?: number; data?: { message?: string; detail?: { message?: string } } };
  message?: string;
}

/**
 * Derives a user-facing message when both stream and non-stream chat requests fail.
 */
export function getChatErrorMessage(streamErr: unknown, chatErr: unknown): string {
  const err = chatErr ?? streamErr;
  const message = (err as Error)?.message ?? "";
  const isNetworkError = /fetch|network|failed to fetch/i.test(message);

  if (err && typeof err === "object") {
    const e = err as ErrLike;
    if (e.response) {
      const msg = e.response.data?.detail?.message ?? e.response.data?.message;
      if (typeof msg === "string" && msg) return msg;
      if (e.response.status === 502 || e.response.status === 503)
        return "服务暂时不可用，请稍后重试。";
      if (e.response.status === 404)
        return "助手接口未找到（/api/ai/chat）。请确认连接的是 Waifu Tutor 后端，并检查后端端口配置。";
      if (e.response.status) return `请求失败 (${e.response.status})，请稍后重试。`;
    }
  }

  if (isNetworkError)
    return "无法连接助手服务。请确认后端已启动（默认端口 8000）。";
  return "Failed to get response from assistant.";
}
