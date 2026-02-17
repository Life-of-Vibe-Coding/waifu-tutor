export function speakText(text: string): void {
  if (typeof window === "undefined") return;
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.95;
  u.pitch = 1.05;
  window.speechSynthesis.speak(u);
}
