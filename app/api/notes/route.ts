import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const folderIdRaw = searchParams.get("folder_id");
  const folderId = folderIdRaw === null ? undefined : folderIdRaw;
  const db = getDb();
  let sql = "SELECT id, folder_id, subject_id, doc_id, title, content, created_at, updated_at FROM study_notes WHERE user_id = ?";
  const args: (string | null)[] = [DEMO_USER_ID];
  if (folderId !== undefined) {
    if (folderId === "" || folderId === "null") {
      sql += " AND folder_id IS NULL";
    } else {
      sql += " AND folder_id = ?";
      args.push(folderId);
    }
  }
  sql += " ORDER BY updated_at DESC";
  const rows = db.prepare(sql).all(...args) as Record<string, unknown>[];
  return NextResponse.json(rows);
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const title = typeof body.title === "string" ? body.title.trim() : "Untitled";
  const content = typeof body.content === "string" ? body.content : "";
  const folderId = body.folder_id != null && body.folder_id !== "" ? String(body.folder_id) : null;
  const subjectId = body.subject_id != null && body.subject_id !== "" ? String(body.subject_id) : null;
  const docId = body.doc_id != null && body.doc_id !== "" ? String(body.doc_id) : null;
  const id = require("crypto").randomUUID();
  const db = getDb();
  const now = new Date().toISOString();
  db.prepare(
    "INSERT INTO study_notes (id, user_id, folder_id, subject_id, doc_id, title, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
  ).run(id, DEMO_USER_ID, folderId, subjectId, docId, title, content, now, now);
  const row = db.prepare(
    "SELECT id, folder_id, subject_id, doc_id, title, content, created_at, updated_at FROM study_notes WHERE id = ?"
  ).get(id) as Record<string, unknown>;
  return NextResponse.json(row);
}
