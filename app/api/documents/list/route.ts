import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

export async function GET() {
  const db = getDb();
  const rows = db.prepare(
    "SELECT id, subject_id, title, filename, mime_type, size_bytes, status, word_count, topic_hint, difficulty_estimate, created_at, updated_at FROM documents WHERE user_id = ? ORDER BY created_at DESC"
  ).all(DEMO_USER_ID) as Record<string, unknown>[];
  return NextResponse.json(rows);
}
