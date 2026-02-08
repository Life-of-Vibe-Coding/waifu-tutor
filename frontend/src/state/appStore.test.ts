import { describe, expect, it } from "vitest";

import { useAppStore } from "./appStore";

describe("appStore", () => {
  it("toggles tts and tracks mood", () => {
    useAppStore.setState({ activeDocId: null, mood: "neutral", ttsEnabled: false, messages: [] });

    useAppStore.getState().toggleTts();
    useAppStore.getState().setMood("happy");

    expect(useAppStore.getState().ttsEnabled).toBe(true);
    expect(useAppStore.getState().mood).toBe("happy");
  });
});
