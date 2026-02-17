import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ folderId: string }> }
) {
  const { folderId } = await params;
  const body = await req.json().catch(() => ({}));
  const db = getDb();
  const row = db.prepare("SELECT id FROM note_folders WHERE id = ? AND user_id = ?").get(folderId, DEMO_USER_ID);
  if (!row) {
    return NextResponse.json({ code: "not_found", message: "Folder not found" }, { status: 404 });
  }
  const now = new Date().toISOString();
  if (body.name !== undefined) {
    const name = String(body.name).trim();
    if (!name) return NextResponse.json({ code: "invalid", message: "name cannot be empty" }, { status: 400 });
    db.prepare("UPDATE note_folders SET name = ?, updated_at = ? WHERE id = ?").run(name, now, folderId);
  }
  if (body.sort_order !== undefined) {
    db.prepare("UPDATE note_folders SET sort_order = ?, updated_at = ? WHERE id = ?").run(Number(body.sort_order), now, folderId);
  }
  const updated = db.prepare(
    "SELECT id, name, parent_id, sort_order, created_at, updated_at FROM note_folders WHERE id = ?"
  ).get(folderId) as Record<string, unknown>;
  return NextResponse.json(updated);
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ folderId: string }> }
) {
  const { folderId } = await params;
  const db = getDb();
  const row = db.prepare("SELECT id FROM note_folders WHERE id = ? AND user_id = ?").get(folderId, DEMO_USER_ID);
  if (!row) {
    return NextResponse.json({ code: "not_found", message: "Folder not found" }, { status: 404 });
  }
  db.prepare("UPDATE study_notes SET folder_id = NULL WHERE folder_id = ?").run(folderId);
  db.prepare("DELETE FROM note_folders WHERE id = ?").run(folderId);
  return NextResponse.json({ ok: true });
}
