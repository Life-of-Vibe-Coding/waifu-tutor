import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ noteId: string }> }
) {
  const { noteId } = await params;
  const db = getDb();
  const row = db.prepare(
    "SELECT id, folder_id, subject_id, doc_id, title, content, created_at, updated_at FROM study_notes WHERE id = ? AND user_id = ?"
  ).get(noteId, DEMO_USER_ID) as Record<string, unknown> | undefined;
  if (!row) {
    return NextResponse.json({ code: "not_found", message: "Note not found" }, { status: 404 });
  }
  return NextResponse.json(row);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ noteId: string }> }
) {
  const { noteId } = await params;
  const body = await req.json().catch(() => ({}));
  const db = getDb();
  const row = db.prepare("SELECT id FROM study_notes WHERE id = ? AND user_id = ?").get(noteId, DEMO_USER_ID);
  if (!row) {
    return NextResponse.json({ code: "not_found", message: "Note not found" }, { status: 404 });
  }
  const now = new Date().toISOString();
  const updates: string[] = ["updated_at = ?"];
  const args: unknown[] = [now];
  if (body.title !== undefined) {
    updates.push("title = ?");
    args.push(typeof body.title === "string" ? body.title.trim() : "Untitled");
  }
  if (body.content !== undefined) {
    updates.push("content = ?");
    args.push(typeof body.content === "string" ? body.content : "");
  }
  if (body.folder_id !== undefined) {
    updates.push("folder_id = ?");
    args.push(body.folder_id == null || body.folder_id === "" ? null : String(body.folder_id));
  }
  if (body.subject_id !== undefined) {
    updates.push("subject_id = ?");
    args.push(body.subject_id == null || body.subject_id === "" ? null : String(body.subject_id));
  }
  if (body.doc_id !== undefined) {
    updates.push("doc_id = ?");
    args.push(body.doc_id == null || body.doc_id === "" ? null : String(body.doc_id));
  }
  if (updates.length > 1) {
    args.push(noteId);
    db.prepare(`UPDATE study_notes SET ${updates.join(", ")} WHERE id = ?`).run(...args);
  }
  const updated = db.prepare(
    "SELECT id, folder_id, subject_id, doc_id, title, content, created_at, updated_at FROM study_notes WHERE id = ?"
  ).get(noteId) as Record<string, unknown>;
  return NextResponse.json(updated);
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ noteId: string }> }
) {
  const { noteId } = await params;
  const db = getDb();
  const row = db.prepare("SELECT id FROM study_notes WHERE id = ? AND user_id = ?").get(noteId, DEMO_USER_ID);
  if (!row) {
    return NextResponse.json({ code: "not_found", message: "Note not found" }, { status: 404 });
  }
  db.prepare("DELETE FROM study_notes WHERE id = ?").run(noteId);
  return NextResponse.json({ ok: true });
}
