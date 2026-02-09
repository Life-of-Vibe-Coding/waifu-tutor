import { describe, expect, it } from "vitest";

import { useAppStore } from "./appStore";

describe("appStore", () => {
  const resetStore = () => {
    useAppStore.setState({
      activeDocId: null,
      mood: "neutral",
      companionStatus: "idle",
      affection: 40,
      sessionStreak: 0,
      lastInteractionAt: null,
      ttsEnabled: false,
      isListening: false,
      messages: [],
    });
  };

  it("toggles tts and tracks mood", () => {
    resetStore();

    useAppStore.getState().toggleTts();
    useAppStore.getState().setMood("happy");

    expect(useAppStore.getState().ttsEnabled).toBe(true);
    expect(useAppStore.getState().mood).toBe("happy");
  });

  it("sets listening state", () => {
    resetStore();

    useAppStore.getState().setListening(true);
    expect(useAppStore.getState().isListening).toBe(true);

    useAppStore.getState().setListening(false);
    expect(useAppStore.getState().isListening).toBe(false);
  });

  it("clamps affection between 0 and 100", () => {
    resetStore();
    useAppStore.setState({ affection: 98 });

    useAppStore.getState().bumpAffection(20);
    expect(useAppStore.getState().affection).toBe(100);

    useAppStore.getState().bumpAffection(-500);
    expect(useAppStore.getState().affection).toBe(0);
  });

  it("updates companion status and streak", () => {
    resetStore();

    useAppStore.getState().setCompanionStatus("listening");
    useAppStore.getState().incrementSessionStreak();
    useAppStore.getState().setCompanionStatus("thinking");
    useAppStore.getState().setCompanionStatus("celebrating");
    useAppStore.getState().setCompanionStatus("idle");

    expect(useAppStore.getState().companionStatus).toBe("idle");
    expect(useAppStore.getState().sessionStreak).toBe(1);

    useAppStore.getState().resetSessionStreak();
    expect(useAppStore.getState().sessionStreak).toBe(0);
  });

  it("can move to comforting state for error path", () => {
    resetStore();
    useAppStore.getState().setCompanionStatus("comforting");
    expect(useAppStore.getState().companionStatus).toBe("comforting");
  });
});
