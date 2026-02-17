import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

export async function GET() {
  const db = getDb();
  const rows = db.prepare(
    "SELECT id, name, parent_id, sort_order, created_at, updated_at FROM note_folders WHERE user_id = ? ORDER BY sort_order ASC, created_at ASC"
  ).all(DEMO_USER_ID) as Record<string, unknown>[];
  return NextResponse.json(rows);
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const name = typeof body.name === "string" ? body.name.trim() : "";
  if (!name) {
    return NextResponse.json({ code: "invalid", message: "name is required" }, { status: 400 });
  }
  const id = require("crypto").randomUUID();
  const parentId = body.parent_id != null ? String(body.parent_id) : null;
  const db = getDb();
  const now = new Date().toISOString();
  db.prepare(
    "INSERT INTO note_folders (id, user_id, name, parent_id, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?)"
  ).run(id, DEMO_USER_ID, name, parentId, now, now);
  const row = db.prepare(
    "SELECT id, name, parent_id, sort_order, created_at, updated_at FROM note_folders WHERE id = ?"
  ).get(id) as Record<string, unknown>;
  return NextResponse.json(row);
}
