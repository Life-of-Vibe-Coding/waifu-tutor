import { describe, it, expect } from "vitest";
import { getChatErrorMessage } from "./chat-error";

describe("getChatErrorMessage", () => {
  it("returns backend detail.message when present", () => {
    const err = { response: { data: { detail: { message: "Message required" } } } };
    expect(getChatErrorMessage(null, err)).toBe("Message required");
  });

  it("returns backend data.message when present", () => {
    const err = { response: { data: { message: "Invalid request" } } };
    expect(getChatErrorMessage(err, null)).toBe("Invalid request");
  });

  it("returns 502/503 service-unavailable message", () => {
    expect(getChatErrorMessage(null, { response: { status: 502 } })).toBe(
      "服务暂时不可用，请稍后重试。"
    );
    expect(getChatErrorMessage(null, { response: { status: 503 } })).toBe(
      "服务暂时不可用，请稍后重试。"
    );
  });

  it("returns generic status message for non-404 HTTP errors", () => {
    expect(getChatErrorMessage(null, { response: { status: 500 } })).toBe(
      "请求失败 (500)，请稍后重试。"
    );
  });

  it("returns route hint for 404", () => {
    expect(getChatErrorMessage(null, { response: { status: 404 } })).toBe(
      "助手接口未找到（/api/ai/chat）。请确认连接的是 Waifu Tutor 后端，并检查后端端口配置。"
    );
  });

  it("returns network hint for fetch/network errors", () => {
    expect(getChatErrorMessage(new Error("Failed to fetch"), null)).toBe(
      "无法连接助手服务。请确认后端已启动（默认端口 8000）。"
    );
    expect(getChatErrorMessage(new Error("Network Error"), null)).toBe(
      "无法连接助手服务。请确认后端已启动（默认端口 8000）。"
    );
  });

  it("prefers chatErr over streamErr", () => {
    const streamErr = new Error("Failed to fetch");
    const chatErr = { response: { data: { message: "Server error" } } };
    expect(getChatErrorMessage(streamErr, chatErr)).toBe("Server error");
  });

  it("falls back to default when no details", () => {
    expect(getChatErrorMessage(null, null)).toBe("Failed to get response from assistant.");
    expect(getChatErrorMessage({}, {})).toBe("Failed to get response from assistant.");
    expect(getChatErrorMessage(new Error("Unknown"), null)).toBe(
      "Failed to get response from assistant."
    );
  });
});
