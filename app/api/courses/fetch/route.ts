import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { randomUUID } from "crypto";
import { fetchCourseWithQwen } from "@/lib/qwen-course";
import { fetchCourseWithAgent, hasRecording } from "@/lib/school-agent";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";
import { chunkText, topKeywords, estimateDifficulty } from "@/lib/document-parser";
import { embed, summarize } from "@/lib/ai";
import { upsertChunks } from "@/lib/vector-sqlite";

const UPLOAD_DIR = process.env.UPLOAD_DIR || path.join(process.cwd(), "data", "uploads");

async function saveContentAsDocument(rawText: string, url: string): Promise<Record<string, unknown>> {
  const docId = randomUUID();
  if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR, { recursive: true });
  const safeName = `${docId}.txt`;
  const storagePath = path.join(UPLOAD_DIR, safeName);
  fs.writeFileSync(storagePath, rawText, "utf8");

  const db = getDb();
  const now = new Date().toISOString();
  const sizeBytes = Buffer.byteLength(rawText, "utf8");
  const title = `Course: ${new URL(url).pathname.split("/").filter(Boolean).pop() || "Scraped"}`;

  db.prepare(
    `INSERT INTO documents (id, user_id, title, filename, mime_type, size_bytes, status, word_count, storage_path)
     VALUES (?, ?, ?, ?, 'text/plain', ?, 'processing', 0, ?)`
  ).run(docId, DEMO_USER_ID, title, safeName, sizeBytes, storagePath);

  const chunks = chunkText(rawText);
  const wordCount = rawText.split(/\s+/).length;
  const keywords = topKeywords(rawText, 3);
  const difficulty = estimateDifficulty(wordCount);

  db.prepare("DELETE FROM document_chunks WHERE doc_id = ?").run(docId);
  const chunkRows: { id: string; doc_id: string; chunk_index: number; chunk_text: string }[] = [];
  const payloads: { chunk_id: string; doc_id: string; chunk_text: string }[] = [];
  for (let i = 0; i < chunks.length; i++) {
    const chunkId = randomUUID();
    chunkRows.push({ id: chunkId, doc_id: docId, chunk_index: i, chunk_text: chunks[i] });
    payloads.push({ chunk_id: chunkId, doc_id: docId, chunk_text: chunks[i] });
  }
  const insertChunk = db.prepare(
    "INSERT INTO document_chunks (id, doc_id, chunk_index, chunk_text) VALUES (?, ?, ?, ?)"
  );
  for (const row of chunkRows) {
    insertChunk.run(row.id, row.doc_id, row.chunk_index, row.chunk_text);
  }

  const vectors = await embed(chunks);
  upsertChunks(vectors, payloads);

  const summaryText = await summarize(rawText, "medium");
  const summaryId = randomUUID();
  db.prepare(
    "INSERT INTO summaries (id, doc_id, detail_level, summary_text) VALUES (?, ?, 'medium', ?)"
  ).run(summaryId, docId, summaryText);

  db.prepare(
    `UPDATE documents SET status = 'ready', word_count = ?, topic_hint = ?, difficulty_estimate = ?, updated_at = ? WHERE id = ?`
  ).run(wordCount, keywords.join(", ") || null, difficulty, now, docId);

  return db.prepare(
    "SELECT id, title, filename, mime_type, size_bytes, status, word_count, topic_hint, difficulty_estimate, created_at, updated_at FROM documents WHERE id = ?"
  ).get(docId) as Record<string, unknown>;
}

export async function POST(req: NextRequest) {
  let body: { url?: string; mode?: "record" | "replay" | "qwen" } = {};
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return NextResponse.json({ code: "invalid_body", message: "JSON body required" }, { status: 400 });
  }

  const url = body.url;
  if (!url || typeof url !== "string") {
    return NextResponse.json({ code: "invalid_url", message: "url is required" }, { status: 400 });
  }

  const mode = body.mode ?? (hasRecording(url.trim()) ? "replay" : "qwen");

  try {
    if (mode === "record") {
      const result = await fetchCourseWithAgent({ url: url.trim(), mode: "record" });
      if (result.ok) return NextResponse.json({ code: "unexpected", message: "Record returned content" }, { status: 500 });
      return NextResponse.json({ recorded: true, message: result.message });
    }

    let rawText: string;
    if (mode === "replay") {
      const result = await fetchCourseWithAgent({ url: url.trim(), mode: "replay" });
      if (!result.ok) {
        return NextResponse.json(
          { code: "replay_failed", message: result.message },
          { status: 400 }
        );
      }
      rawText = result.content;
    } else {
      rawText = await fetchCourseWithQwen(url.trim());
    }
    if (!rawText?.trim()) {
      return NextResponse.json(
        { code: "no_content", message: "Could not extract any content from the page" },
        { status: 400 }
      );
    }

    const doc = await saveContentAsDocument(rawText, url.trim());
    return NextResponse.json(doc);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Course fetch failed";
    console.error("[courses/fetch]", err);
    const isClientError =
      msg.includes("login") ||
      msg.includes("too little") ||
      msg.includes("Failed to fetch URL") ||
      msg.includes("Cannot connect to Chrome") ||
      msg.includes("ECONNREFUSED");
    return NextResponse.json(
      { code: "fetch_failed", message: msg },
      { status: isClientError ? 400 : 500 }
    );
  }
}
