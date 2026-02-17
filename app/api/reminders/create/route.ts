import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { title, note, scheduled_for: scheduledFor } = body;
  if (!title || typeof title !== "string" || !title.trim()) {
    return NextResponse.json({ code: "invalid_request", message: "Title required" }, { status: 400 });
  }
  if (!scheduledFor) {
    return NextResponse.json({ code: "invalid_request", message: "scheduled_for required" }, { status: 400 });
  }
  const db = getDb();
  const id = randomUUID();
  const now = new Date().toISOString();
  db.prepare(
    "INSERT INTO reminders (id, user_id, title, note, scheduled_for, completed) VALUES (?, ?, ?, ?, ?, 0)"
  ).run(id, DEMO_USER_ID, title.trim(), note != null ? String(note) : null, scheduledFor);
  const row = db.prepare("SELECT id, title, note, scheduled_for, completed, created_at, updated_at FROM reminders WHERE id = ?").get(id) as Record<string, unknown> & { scheduled_for: string };
  const dueNow = new Date(row.scheduled_for) <= new Date();
  return NextResponse.json({ ...row, due_now: dueNow });
}
