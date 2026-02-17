import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { randomUUID } from "crypto";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";
import { parseDocument, chunkText, topKeywords, estimateDifficulty } from "@/lib/document-parser";
import { embed, summarize, classifySubjectForDocument } from "@/lib/ai";
import { upsertChunks } from "@/lib/vector-sqlite";
import { listSubjects, createSubjectIfNotExists } from "@/lib/subjects";

const UPLOAD_DIR = process.env.UPLOAD_DIR || path.join(process.cwd(), "data", "uploads");
const MAX_UPLOAD_BYTES = Number(process.env.MAX_UPLOAD_BYTES) || 10 * 1024 * 1024;
const ALLOWED = [".pdf", ".docx", ".txt", ".md"];

export async function POST(req: NextRequest) {
  const formData = await req.formData().catch(() => null);
  if (!formData) {
    return NextResponse.json({ code: "invalid_document", message: "No file" }, { status: 400 });
  }
  const file = formData.get("file") as File | null;
  if (!file || typeof file === "string") {
    return NextResponse.json({ code: "invalid_document", message: "No file" }, { status: 400 });
  }
  const size = file.size;
  if (size === 0) {
    return NextResponse.json({ code: "invalid_document", message: "File is empty" }, { status: 400 });
  }
  if (size > MAX_UPLOAD_BYTES) {
    return NextResponse.json(
      { code: "invalid_document", message: `File exceeds max upload size (${MAX_UPLOAD_BYTES} bytes)` },
      { status: 400 }
    );
  }
  const name = file.name || "document.txt";
  const ext = path.extname(name).toLowerCase();
  if (!ALLOWED.includes(ext)) {
    return NextResponse.json({ code: "invalid_document", message: "Unsupported file extension" }, { status: 400 });
  }

  const docId = randomUUID();
  if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR, { recursive: true });
  const safeName = `${docId}${ext}`;
  const storagePath = path.join(UPLOAD_DIR, safeName);
  const buf = Buffer.from(await file.arrayBuffer());
  fs.writeFileSync(storagePath, buf);

  const db = getDb();
  const now = new Date().toISOString();
  db.prepare(
    `INSERT INTO documents (id, user_id, subject_id, title, filename, mime_type, size_bytes, status, word_count, storage_path)
     VALUES (?, ?, ?, ?, ?, ?, ?, 'processing', 0, ?)`
  ).run(docId, DEMO_USER_ID, null, path.basename(name, ext), name, file.type || "application/octet-stream", size, storagePath);

  try {
    const rawText = (await parseDocument(storagePath)).trim();
    if (!rawText) {
      throw new Error("No readable text extracted from document");
    }
    const title = path.basename(name, ext);
    const existingSubjects = listSubjects(DEMO_USER_ID);
    const classification = await classifySubjectForDocument(
      title,
      null,
      rawText,
      existingSubjects.map((s) => ({ id: s.id, name: s.name }))
    );
    let subjectIdToSet: string | null = null;
    let suggestedSubjectId: string | null = null;
    let suggestedSubjectName: string | null = null;
    let needsConfirmation = false;
    if (classification.is_new) {
      const subject = createSubjectIfNotExists(DEMO_USER_ID, classification.subject_name);
      subjectIdToSet = subject.id;
      db.prepare("UPDATE documents SET subject_id = ? WHERE id = ?").run(subjectIdToSet, docId);
    } else if (classification.subject_id) {
      suggestedSubjectId = classification.subject_id;
      suggestedSubjectName = classification.subject_name;
      needsConfirmation = true;
      // Do not set subject_id until user confirms
    }
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

    const doc = db.prepare(
      "SELECT id, subject_id, title, filename, mime_type, size_bytes, status, word_count, topic_hint, difficulty_estimate, created_at, updated_at FROM documents WHERE id = ?"
    ).get(docId) as Record<string, unknown>;
    const response: Record<string, unknown> = { ...doc };
    if (needsConfirmation && suggestedSubjectId && suggestedSubjectName) {
      response.suggested_subject_id = suggestedSubjectId;
      response.suggested_subject_name = suggestedSubjectName;
      response.subject_needs_confirmation = true;
    }
    return NextResponse.json(response);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Document processing failed";
    db.prepare("UPDATE documents SET status = 'failed', updated_at = ? WHERE id = ?").run(now, docId);
    return NextResponse.json({ code: "processing_failed", message: msg }, { status: 500 });
  }
}
