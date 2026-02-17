/**
 * Rerank candidate passages with DashScope qwen3-rerank (or gte-rerank-v2).
 * Used after fast embedding retrieval for better RAG relevance.
 */

const DASHSCOPE_API_KEY = process.env.DASHSCOPE_API_KEY;
const DASHSCOPE_BASE = process.env.DASHSCOPE_BASE || "https://dashscope-intl.aliyuncs.com";
const RERANK_MODEL = process.env.RERANK_MODEL || "qwen3-rerank";
const RERANK_URL = `${DASHSCOPE_BASE}/compatible-api/v1/reranks`;

const MAX_DOCS = 50;
const MAX_TOKENS_PER_ITEM = 4000;

/** Truncate text to roughly max tokens (chars ~= tokens for English/Chinese). */
function truncate(text: string, maxChars: number = MAX_TOKENS_PER_ITEM * 2): string {
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars) + "...";
}

export interface RerankResult {
  index: number;
  relevance_score: number;
  text?: string;
}

/**
 * Rerank documents by relevance to the query. Returns top_n results in order.
 * If API is unavailable or documents empty, returns candidates in original order with score 1.
 */
export async function rerank(
  query: string,
  documents: string[],
  topN: number = 10
): Promise<RerankResult[]> {
  if (!documents.length) return [];
  if (!DASHSCOPE_API_KEY) {
    return documents.slice(0, topN).map((text, i) => ({ index: i, relevance_score: 1, text }));
  }
  const toSend = documents.slice(0, MAX_DOCS).map((d) => truncate(d));
  try {
    const res = await fetch(RERANK_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${DASHSCOPE_API_KEY}`,
      },
      body: JSON.stringify({
        model: RERANK_MODEL,
        query: query.slice(0, 4000),
        documents: toSend,
        top_n: Math.min(topN, toSend.length),
        instruct: "Given a web search query, retrieve relevant passages that answer the query.",
      }),
    });
    if (!res.ok) {
      return documents.slice(0, topN).map((text, i) => ({ index: i, relevance_score: 1, text }));
    }
    const data = (await res.json()) as {
      results?: Array<{ index: number; relevance_score: number; document?: { text?: string } }>;
    };
    const results = data.results ?? [];
    return results.map((r) => ({
      index: r.index,
      relevance_score: r.relevance_score,
      text: r.document?.text ?? toSend[r.index],
    }));
  } catch {
    return documents.slice(0, topN).map((text, i) => ({ index: i, relevance_score: 1, text }));
  }
}

/**
 * Rerank search results (with chunk_id, doc_id, text, score) by query.
 * Returns the same shape array, reordered and with updated scores from reranker.
 */
export async function rerankSearchResults<T extends { text: string }>(
  query: string,
  candidates: T[],
  topN: number = 10
): Promise<T[]> {
  if (candidates.length === 0) return [];
  const texts = candidates.map((c) => c.text);
  const reranked = await rerank(query, texts, topN);
  return reranked.map((r) => candidates[r.index]);
}
