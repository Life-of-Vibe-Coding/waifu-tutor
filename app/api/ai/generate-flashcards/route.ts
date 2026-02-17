import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { getDb } from "@/lib/db";
import { generateFlashcards } from "@/lib/ai";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { doc_id: docId, max_cards: maxCards = 12 } = body;
  if (!docId) {
    return NextResponse.json({ code: "not_found", message: "Document not found" }, { status: 404 });
  }
  const db = getDb();
  const doc = db.prepare("SELECT id FROM documents WHERE id = ?").get(docId);
  if (!doc) {
    return NextResponse.json({ code: "not_found", message: "Document not found" }, { status: 404 });
  }
  const existing = db.prepare("SELECT id, doc_id, question, answer, explanation, created_at, repetitions, interval_days, ease_factor, last_reviewed_at, next_review_at FROM flashcards WHERE doc_id = ? LIMIT ?").all(docId, maxCards) as Record<string, unknown>[];
  if (existing.length) {
    return NextResponse.json(existing);
  }
  const chunks = db.prepare("SELECT chunk_text FROM document_chunks WHERE doc_id = ? ORDER BY chunk_index ASC").all(docId) as { chunk_text: string }[];
  const sourceText = chunks.map((c) => c.chunk_text).join("\n");
  if (!sourceText.trim()) {
    return NextResponse.json({ code: "empty_document", message: "No text available for flashcards" }, { status: 400 });
  }
  const cards = await generateFlashcards(sourceText, maxCards);
  const insert = db.prepare(
    "INSERT INTO flashcards (id, doc_id, question, answer, explanation, repetitions, interval_days, ease_factor) VALUES (?, ?, ?, ?, ?, 0, 1, 2.5)"
  );
  for (const card of cards) {
    insert.run(randomUUID(), docId, card.question, card.answer, card.explanation ?? null);
  }
  const rows = db.prepare("SELECT id, doc_id, question, answer, explanation, created_at, repetitions, interval_days, ease_factor, last_reviewed_at, next_review_at FROM flashcards WHERE doc_id = ? ORDER BY created_at ASC").all(docId) as Record<string, unknown>[];
  return NextResponse.json(rows);
}
