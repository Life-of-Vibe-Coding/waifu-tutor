import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { getDb } from "@/lib/db";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: cardId } = await params;
  const body = await req.json().catch(() => ({}));
  const quality = Math.min(5, Math.max(0, Number(body.quality) ?? 0));
  const userAnswer = body.user_answer != null ? String(body.user_answer) : null;

  const db = getDb();
  const card = db.prepare(
    "SELECT id, doc_id, question, answer, explanation, created_at, repetitions, interval_days, ease_factor, last_reviewed_at, next_review_at FROM flashcards WHERE id = ?"
  ).get(cardId) as Record<string, unknown> | undefined;
  if (!card) {
    return NextResponse.json({ code: "not_found", message: "Flashcard not found" }, { status: 404 });
  }

  let repetitions = Number(card.repetitions) || 0;
  let interval = Number(card.interval_days) || 1;
  let ease = Number(card.ease_factor) || 2.5;

  if (quality < 3) {
    repetitions = 0;
    interval = 1;
  } else {
    if (repetitions === 0) interval = 1;
    else if (repetitions === 1) interval = 6;
    else interval = Math.max(1, Math.round(interval * ease));
    repetitions++;
  }
  ease = Math.max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)));
  const now = new Date().toISOString();
  const nextReview = new Date(Date.now() + interval * 24 * 60 * 60 * 1000).toISOString();

  db.prepare(
    "INSERT INTO flashcard_reviews (id, card_id, quality, repetitions, interval_days, ease_factor, user_answer) VALUES (?, ?, ?, ?, ?, ?, ?)"
  ).run(randomUUID(), cardId, quality, repetitions, interval, ease, userAnswer);
  db.prepare(
    "UPDATE flashcards SET repetitions = ?, interval_days = ?, ease_factor = ?, last_reviewed_at = ?, next_review_at = ? WHERE id = ?"
  ).run(repetitions, interval, ease, now, nextReview, cardId);

  const progress = db.prepare("SELECT total_reviews, cards_reviewed_today, average_score FROM study_progress LIMIT 1").get() as { total_reviews: number; cards_reviewed_today: number; average_score: number } | undefined;
  if (progress) {
    const totalReviews = progress.total_reviews + 1;
    const newAvg = (progress.average_score * progress.total_reviews + quality) / totalReviews;
    db.prepare(
      "UPDATE study_progress SET cards_reviewed_today = cards_reviewed_today + 1, total_reviews = ?, average_score = ?, updated_at = ?"
    ).run(totalReviews, newAvg, now);
  }

  const updated = db.prepare(
    "SELECT id, doc_id, question, answer, explanation, created_at, repetitions, interval_days, ease_factor, last_reviewed_at, next_review_at FROM flashcards WHERE id = ?"
  ).get(cardId) as Record<string, unknown>;
  return NextResponse.json(updated);
}
