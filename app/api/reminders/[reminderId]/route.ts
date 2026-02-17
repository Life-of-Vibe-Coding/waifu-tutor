import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ reminderId: string }> }
) {
  const { reminderId } = await params;
  const body = await req.json().catch(() => ({}));
  const db = getDb();
  const row = db.prepare("SELECT id, title, note, scheduled_for, completed FROM reminders WHERE id = ? AND user_id = ?").get(reminderId, DEMO_USER_ID) as Record<string, unknown> | undefined;
  if (!row) {
    return NextResponse.json({ code: "not_found", message: "Reminder not found" }, { status: 404 });
  }
  const now = new Date().toISOString();
  if (body.title !== undefined) db.prepare("UPDATE reminders SET title = ?, updated_at = ? WHERE id = ?").run(String(body.title), now, reminderId);
  if (body.note !== undefined) db.prepare("UPDATE reminders SET note = ?, updated_at = ? WHERE id = ?").run(body.note == null ? null : String(body.note), now, reminderId);
  if (body.scheduled_for !== undefined) db.prepare("UPDATE reminders SET scheduled_for = ?, updated_at = ? WHERE id = ?").run(body.scheduled_for, now, reminderId);
  if (body.completed !== undefined) db.prepare("UPDATE reminders SET completed = ?, updated_at = ? WHERE id = ?").run(body.completed ? 1 : 0, now, reminderId);
  const updated = db.prepare("SELECT id, title, note, scheduled_for, completed, created_at, updated_at FROM reminders WHERE id = ?").get(reminderId) as Record<string, unknown> & { scheduled_for: string };
  return NextResponse.json({ ...updated, due_now: new Date(updated.scheduled_for) <= new Date() });
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ reminderId: string }> }
) {
  const { reminderId } = await params;
  const db = getDb();
  const row = db.prepare("SELECT id FROM reminders WHERE id = ? AND user_id = ?").get(reminderId, DEMO_USER_ID);
  if (!row) {
    return NextResponse.json({ code: "not_found", message: "Reminder not found" }, { status: 404 });
  }
  db.prepare("DELETE FROM reminders WHERE id = ?").run(reminderId);
  return NextResponse.json({ ok: true });
}
