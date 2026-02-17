export type Mood = "happy" | "encouraging" | "sad" | "neutral" | "excited";

export function moodFromScore(score: number): Mood {
  if (score >= 90) return "excited";
  if (score >= 70) return "happy";
  if (score >= 50) return "encouraging";
  if (score >= 30) return "neutral";
  return "sad";
}

export function moodFromText(_text: string): Mood {
  return "encouraging";
}
