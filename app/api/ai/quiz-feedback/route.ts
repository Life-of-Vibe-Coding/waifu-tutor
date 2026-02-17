import { NextRequest, NextResponse } from "next/server";
import { chat } from "@/lib/ai";
import { moodFromScore } from "@/lib/mood";

function ratio(a: string, b: string): number {
  const sa = a.toLowerCase().trim();
  const sb = b.toLowerCase().trim();
  if (sa === sb) return 1;
  let matches = 0;
  const maxLen = Math.max(sa.length, sb.length);
  for (let i = 0; i < maxLen; i++) {
    if (sa[i] === sb[i]) matches++;
  }
  return maxLen ? matches / maxLen : 0;
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { question, expected_answer: expectedAnswer, user_answer: userAnswer } = body;
  if (!question || expectedAnswer === undefined || userAnswer === undefined) {
    return NextResponse.json({ code: "invalid_request", message: "Missing fields" }, { status: 400 });
  }
  const score = Math.round(ratio(String(expectedAnswer), String(userAnswer)) * 100);
  const mood = moodFromScore(score);
  const coachingPrompt = `Give concise quiz feedback. Question, expected answer, student answer are below. Be constructive and encouraging.\n\nQuestion: ${question}\nExpected: ${expectedAnswer}\nStudent: ${userAnswer}\nScore: ${score}`;
  const feedback = await chat(coachingPrompt, []);
  return NextResponse.json({ score, feedback, mood });
}
