import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";
import { organizeMaterials, type DocSummaryForOrganize } from "@/lib/ai";

/** POST: optional body { doc_ids?: string[] }. If empty, use all ready docs for the user. */
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const docIds = body.doc_ids as string[] | undefined;

  const db = getDb();
  const ids: string[] = Array.isArray(docIds) && docIds.length > 0
    ? docIds
    : (db
        .prepare(
          "SELECT id FROM documents WHERE user_id = ? AND status = 'ready' ORDER BY created_at DESC"
        )
        .all(DEMO_USER_ID) as { id: string }[]
      ).map((r) => r.id);

  if (ids.length === 0) {
    return NextResponse.json(
      { code: "no_documents", message: "No documents to organize. Upload PDF or TXT first." },
      { status: 400 }
    );
  }

  const placeholders = ids.map(() => "?").join(",");
  const docs = db.prepare(
    `SELECT id, title, topic_hint FROM documents WHERE id IN (${placeholders}) AND user_id = ?`
  ).all(...ids, DEMO_USER_ID) as { id: string; title: string; topic_hint: string | null }[];

  const summaryRows = db
    .prepare(
      `SELECT doc_id, summary_text FROM summaries WHERE doc_id IN (${placeholders}) AND detail_level = 'medium'`
    )
    .all(...ids) as { doc_id: string; summary_text: string }[];
  const summaryByDoc = Object.fromEntries(summaryRows.map((r) => [r.doc_id, r.summary_text]));

  const payload: DocSummaryForOrganize[] = docs.map((d) => ({
    title: d.title,
    topicHint: d.topic_hint,
    summary: summaryByDoc[d.id] ?? "(暂无摘要)",
  }));

  try {
    const organization = await organizeMaterials(payload);
    return NextResponse.json({ organization });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Failed to organize materials";
    return NextResponse.json({ code: "organize_failed", message: msg }, { status: 500 });
  }
}
