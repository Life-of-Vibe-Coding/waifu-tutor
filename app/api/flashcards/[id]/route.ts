import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: docId } = await params;
  const db = getDb();
  const rows = db.prepare(
    "SELECT id, doc_id, question, answer, explanation, created_at, repetitions, interval_days, ease_factor, last_reviewed_at, next_review_at FROM flashcards WHERE doc_id = ? ORDER BY created_at ASC"
  ).all(docId) as Record<string, unknown>[];
  return NextResponse.json(rows);
}
