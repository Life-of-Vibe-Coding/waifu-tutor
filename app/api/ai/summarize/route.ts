import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { summarize } from "@/lib/ai";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { doc_id: docId, detail_level: detailLevel = "medium", force_refresh: forceRefresh = false } = body;
  if (!docId) {
    return NextResponse.json({ code: "not_found", message: "Document not found" }, { status: 404 });
  }
  const db = getDb();
  const doc = db.prepare("SELECT id FROM documents WHERE id = ?").get(docId);
  if (!doc) {
    return NextResponse.json({ code: "not_found", message: "Document not found" }, { status: 404 });
  }
  if (!forceRefresh) {
    const cached = db.prepare("SELECT summary_text, generated_at FROM summaries WHERE doc_id = ? AND detail_level = ?").get(docId, detailLevel) as { summary_text: string; generated_at: string } | undefined;
    if (cached) {
      return NextResponse.json({
        doc_id: docId,
        detail_level: detailLevel,
        summary_text: cached.summary_text,
        cached: true,
        generated_at: cached.generated_at,
      });
    }
  }
  const chunks = db.prepare("SELECT chunk_text FROM document_chunks WHERE doc_id = ? ORDER BY chunk_index ASC").all(docId) as { chunk_text: string }[];
  const fullText = chunks.map((c) => c.chunk_text).join("\n\n");
  if (!fullText.trim()) {
    return NextResponse.json({ code: "empty_document", message: "No text available for summary" }, { status: 400 });
  }
  const summaryText = await summarize(fullText, detailLevel);
  const { randomUUID } = require("crypto");
  db.prepare("INSERT INTO summaries (id, doc_id, detail_level, summary_text) VALUES (?, ?, ?, ?)").run(randomUUID(), docId, detailLevel, summaryText);
  const row = db.prepare("SELECT generated_at FROM summaries WHERE doc_id = ? AND detail_level = ? ORDER BY generated_at DESC LIMIT 1").get(docId, detailLevel) as { generated_at: string };
  return NextResponse.json({
    doc_id: docId,
    detail_level: detailLevel,
    summary_text: summaryText,
    cached: false,
    generated_at: row.generated_at,
  });
}
