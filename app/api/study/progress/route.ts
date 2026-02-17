import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function GET() {
  const db = getDb();
  const totalDocuments = (db.prepare("SELECT COUNT(*) as c FROM documents").get() as { c: number }).c;
  const totalFlashcards = (db.prepare("SELECT COUNT(*) as c FROM flashcards").get() as { c: number }).c;
  const now = new Date().toISOString();
  const cardsDue = (db.prepare("SELECT COUNT(*) as c FROM flashcards WHERE next_review_at IS NOT NULL AND next_review_at <= ?").get(now) as { c: number }).c;
  const progress = db.prepare("SELECT cards_reviewed_today, average_score FROM study_progress LIMIT 1").get() as { cards_reviewed_today: number; average_score: number } | undefined;
  return NextResponse.json({
    total_documents: totalDocuments,
    total_flashcards: totalFlashcards,
    cards_due: cardsDue,
    cards_reviewed_today: progress?.cards_reviewed_today ?? 0,
    average_score: progress?.average_score ?? 0,
  });
}
