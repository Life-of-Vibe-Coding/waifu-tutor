import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

export async function GET() {
  const db = getDb();
  const rows = db.prepare(
    "SELECT id, title, note, scheduled_for, completed, created_at, updated_at FROM reminders WHERE user_id = ? ORDER BY scheduled_for ASC"
  ).all(DEMO_USER_ID) as (Record<string, unknown> & { scheduled_for: string })[];
  const now = new Date();
  const list = rows.map((r) => ({ ...r, due_now: new Date(r.scheduled_for) <= now }));
  return NextResponse.json(list);
}
