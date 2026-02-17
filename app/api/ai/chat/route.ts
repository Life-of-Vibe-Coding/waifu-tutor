import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { hybridSearch, getChunksForDocument } from "@/lib/search";
import { embed } from "@/lib/ai";
import { chat } from "@/lib/ai";
import { moodFromText } from "@/lib/mood";
import { rerankSearchResults } from "@/lib/reranker";

const RETRIEVAL_INITIAL_LIMIT = 35;
const RERANK_TOP_N = 10;

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { message, doc_id: docId } = body;
  if (!message || typeof message !== "string" || !message.trim()) {
    return NextResponse.json({ code: "invalid_request", message: "Message required" }, { status: 400 });
  }
  const query = message.trim();
  const queryVector = (await embed([query]))[0];
  let context = hybridSearch(query, docId ?? null, RETRIEVAL_INITIAL_LIMIT, queryVector);
  if (docId && context.length === 0) {
    context = getChunksForDocument(docId, RERANK_TOP_N);
  } else if (context.length > RERANK_TOP_N) {
    context = await rerankSearchResults(query, context, RERANK_TOP_N);
  } else if (context.length > 0) {
    context = await rerankSearchResults(query, context, context.length);
  }
  const attachmentTitle =
    docId && context.length > 0
      ? (getDb().prepare("SELECT title FROM documents WHERE id = ?").get(docId) as { title?: string } | undefined)?.title ?? null
      : null;
  const text = await chat(query, context.map((c) => c.text), attachmentTitle);
  const mood = moodFromText(text);
  return NextResponse.json({
    message: { role: "assistant", content: text, created_at: new Date().toISOString() },
    context: context.map((c) => ({ chunk_id: c.chunk_id, doc_id: c.doc_id, text: c.text, source: c.source, score: c.score })),
    mood,
  });
}
