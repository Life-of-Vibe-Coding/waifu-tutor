import { getDb } from "./db";
import { semanticSearch } from "./vector-sqlite";

export function keywordSearch(query: string, docId: string | null, limit: number): Array<{ chunk_id: string; doc_id: string; text: string; score: number; source: string }> {
  const db = getDb();
  const q = query.trim().replace(/"/g, '""');
  if (!q) return [];
  let rows: { chunk_id: string; doc_id: string; text: string; score: number }[];
  try {
    if (docId) {
      rows = db.prepare(`
        SELECT dc.id AS chunk_id, dc.doc_id, dc.chunk_text AS text, bm25(document_chunks_fts) AS score
        FROM document_chunks_fts
        JOIN document_chunks dc ON dc.rowid = document_chunks_fts.rowid
        WHERE document_chunks_fts MATCH ? AND dc.doc_id = ?
        ORDER BY bm25(document_chunks_fts)
        LIMIT ?
      `).all(q, docId, limit) as { chunk_id: string; doc_id: string; text: string; score: number }[];
    } else {
      rows = db.prepare(`
        SELECT dc.id AS chunk_id, dc.doc_id, dc.chunk_text AS text, bm25(document_chunks_fts) AS score
        FROM document_chunks_fts
        JOIN document_chunks dc ON dc.rowid = document_chunks_fts.rowid
        WHERE document_chunks_fts MATCH ?
        ORDER BY bm25(document_chunks_fts)
        LIMIT ?
      `).all(q, limit) as { chunk_id: string; doc_id: string; text: string; score: number }[];
    }
    return rows.map((row) => ({
      ...row,
      score: -row.score,
      source: "keyword" as const,
    }));
  } catch {
    return [];
  }
}

export function hybridSearch(
  query: string,
  docId: string | null,
  limit: number,
  queryVector: number[] | null
): Array<{ chunk_id: string; doc_id: string; text: string; score: number; source: string }> {
  const keyword = keywordSearch(query, docId, limit);
  const semantic = queryVector ? semanticSearch(queryVector, docId, limit * 2) : [];
  const merged: Record<string, { chunk_id: string; doc_id: string; text: string; score: number; source: string }> = {};
  for (const item of [...keyword, ...semantic]) {
    const key = item.chunk_id;
    if (!merged[key] || item.score > merged[key].score) {
      merged[key] = { ...item, source: item.source };
    }
  }
  return Object.values(merged)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

/** When user selects a document but search returns nothing, use the first chunks of that doc so the agent still reads the attachment. */
export function getChunksForDocument(
  docId: string,
  limit: number
): Array<{ chunk_id: string; doc_id: string; text: string; score: number; source: string }> {
  const db = getDb();
  const rows = db
    .prepare(
      "SELECT id AS chunk_id, doc_id, chunk_text AS text FROM document_chunks WHERE doc_id = ? ORDER BY chunk_index ASC LIMIT ?"
    )
    .all(docId, limit) as { chunk_id: string; doc_id: string; text: string }[];
  return rows.map((r) => ({ ...r, score: 1, source: "document" as const }));
}
