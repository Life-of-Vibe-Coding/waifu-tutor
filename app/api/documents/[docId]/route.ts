import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";
import { deleteDocument } from "@/lib/vector-sqlite";
import { getSubjectById } from "@/lib/subjects";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ docId: string }> }
) {
  const { docId } = await params;
  const db = getDb();
  const doc = db.prepare(
    "SELECT id, subject_id, title, filename, mime_type, size_bytes, status, word_count, topic_hint, difficulty_estimate, created_at, updated_at FROM documents WHERE id = ? AND user_id = ?"
  ).get(docId, DEMO_USER_ID) as Record<string, unknown> | undefined;
  if (!doc) {
    return NextResponse.json({ code: "not_found", message: "Document not found" }, { status: 404 });
  }
  return NextResponse.json(doc);
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ docId: string }> }
) {
  const { docId } = await params;
  const db = getDb();
  const doc = db.prepare("SELECT id, storage_path FROM documents WHERE id = ? AND user_id = ?").get(docId, DEMO_USER_ID) as { id: string; storage_path: string } | undefined;
  if (!doc) {
    return NextResponse.json({ code: "not_found", message: "Document not found" }, { status: 404 });
  }
  try {
    if (fs.existsSync(doc.storage_path)) fs.unlinkSync(doc.storage_path);
  } catch (_) {}
  deleteDocument(docId);
  db.prepare("DELETE FROM documents WHERE id = ?").run(docId);
  return NextResponse.json({ ok: true });
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ docId: string }> }
) {
  const { docId } = await params;
  const body = await req.json().catch(() => ({}));
  const { subject_id: subjectId } = body;
  const db = getDb();
  const doc = db.prepare("SELECT id, user_id FROM documents WHERE id = ? AND user_id = ?").get(docId, DEMO_USER_ID) as { id: string } | undefined;
  if (!doc) {
    return NextResponse.json({ code: "not_found", message: "Document not found" }, { status: 404 });
  }
  if (subjectId !== undefined && subjectId !== null) {
    if (typeof subjectId !== "string") {
      return NextResponse.json({ code: "invalid_request", message: "subject_id must be a string or null" }, { status: 400 });
    }
    const subject = getSubjectById(subjectId);
    if (!subject || subject.user_id !== DEMO_USER_ID) {
      return NextResponse.json({ code: "not_found", message: "Subject not found" }, { status: 404 });
    }
    db.prepare("UPDATE documents SET subject_id = ?, updated_at = ? WHERE id = ?").run(subjectId, new Date().toISOString(), docId);
  } else {
    db.prepare("UPDATE documents SET subject_id = NULL, updated_at = ? WHERE id = ?").run(new Date().toISOString(), docId);
  }
  const updated = db.prepare(
    "SELECT id, subject_id, title, filename, mime_type, size_bytes, status, word_count, topic_hint, difficulty_estimate, created_at, updated_at FROM documents WHERE id = ?"
  ).get(docId) as Record<string, unknown>;
  return NextResponse.json(updated);
}
