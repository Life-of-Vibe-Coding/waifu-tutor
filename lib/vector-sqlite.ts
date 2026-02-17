import { getDb } from "./db";

const EMBEDDING_DIM = Number(process.env.EMBEDDING_DIM) || 1536;

export function upsertChunks(vectors: number[][], payloads: { chunk_id: string; doc_id: string; chunk_text: string }[]) {
  if (vectors.length === 0) return;
  const db = getDb();
  const insert = db.prepare(
    "INSERT OR REPLACE INTO chunk_embeddings (chunk_id, doc_id, embedding) VALUES (?, ?, ?)"
  );
  const toBlob = (vec: number[]) => Buffer.from(new Float32Array(vec).buffer);
  for (let i = 0; i < vectors.length; i++) {
    insert.run(payloads[i].chunk_id, payloads[i].doc_id, toBlob(vectors[i]));
  }
}

export function deleteDocument(docId: string) {
  getDb().prepare("DELETE FROM chunk_embeddings WHERE doc_id = ?").run(docId);
}

function fromBlob(blob: Buffer): number[] {
  return Array.from(new Float32Array(blob.buffer, blob.byteOffset, blob.length / 4));
}

function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  const denom = Math.sqrt(na) * Math.sqrt(nb);
  return denom ? dot / denom : 0;
}

export function semanticSearch(queryVector: number[], docId: string | null, limit: number): Array<{ chunk_id: string; doc_id: string; text: string; score: number; source: string }> {
  const db = getDb();
  const rows = docId
    ? db.prepare("SELECT chunk_id, doc_id, embedding FROM chunk_embeddings WHERE doc_id = ?").all(docId) as { chunk_id: string; doc_id: string; embedding: Buffer }[]
    : db.prepare("SELECT chunk_id, doc_id, embedding FROM chunk_embeddings").all() as { chunk_id: string; doc_id: string; embedding: Buffer }[];

  const chunkTexts = new Map<string, string>();
  for (const r of rows) {
    const row = db.prepare("SELECT chunk_text FROM document_chunks WHERE id = ?").get(r.chunk_id) as { chunk_text: string } | undefined;
    if (row) chunkTexts.set(r.chunk_id, row.chunk_text);
  }

  const results: { chunk_id: string; doc_id: string; text: string; score: number; source: string }[] = [];
  for (const r of rows) {
    const vec = fromBlob(r.embedding);
    const score = cosineSimilarity(queryVector, vec);
    const text = chunkTexts.get(r.chunk_id) ?? "";
    results.push({ chunk_id: r.chunk_id, doc_id: r.doc_id, text, score, source: "semantic" });
  }
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, limit);
}
