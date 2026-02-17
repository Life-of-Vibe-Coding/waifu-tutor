import { getDb } from "./db";
import { DEMO_USER_ID } from "./constants";
import { AGENT_PERSONA } from "./persona";

const EMBEDDING_DIM = Number(process.env.EMBEDDING_DIM) || 1536;
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-2.0-flash";
const GEMINI_EMBED_MODEL = process.env.GEMINI_EMBED_MODEL || "text-embedding-004";

// Qwen3 Flash (DashScope OpenAI-compatible)
const DASHSCOPE_API_KEY = process.env.DASHSCOPE_API_KEY;
const DASHSCOPE_BASE = process.env.DASHSCOPE_BASE || "https://dashscope-intl.aliyuncs.com";
const QWEN_MODEL = process.env.QWEN_MODEL || "qwen-flash";
const QWEN_CHAT_URL = `${DASHSCOPE_BASE}/compatible-mode/v1/chat/completions`;

import { GoogleGenerativeAI } from "@google/generative-ai";

let genAI: InstanceType<typeof GoogleGenerativeAI> | null = null;

function getClient(): InstanceType<typeof GoogleGenerativeAI> | null {
  if (!genAI && process.env.GEMINI_API_KEY) {
    genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  }
  return genAI;
}

/** Call Qwen (DashScope) chat completions; returns content or null on failure. */
async function qwenComplete(messages: { role: "system" | "user"; content: string }[]): Promise<string | null> {
  if (!DASHSCOPE_API_KEY) return null;
  try {
    const res = await fetch(QWEN_CHAT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${DASHSCOPE_API_KEY}`,
      },
      body: JSON.stringify({ model: QWEN_MODEL, messages }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { choices?: Array<{ message?: { content?: string } }> };
    const content = data.choices?.[0]?.message?.content?.trim();
    return content ?? null;
  } catch {
    return null;
  }
}

function logUsage(endpoint: string, latencyMs: number, model: string = GEMINI_MODEL) {
  try {
    const db = getDb();
    const { randomUUID } = require("crypto");
    db.prepare(
      "INSERT INTO ai_usage_logs (id, user_id, endpoint, model, latency_ms) VALUES (?, ?, ?, ?, ?)"
    ).run(randomUUID(), DEMO_USER_ID, endpoint, model, latencyMs);
  } catch (_) {}
}

export async function summarize(text: string, detailLevel: string): Promise<string> {
  const start = Date.now();
  const userPrompt = `Summarize the following document in ${detailLevel} detail: include key concepts and action items. Keep the tone warm and encouraging, as if you're a cute study buddy helping them get the gist. Do not add filler—stay focused on the content.

Document:
${text.slice(0, 12000)}`;
  const outQwen = await qwenComplete([
    { role: "system", content: AGENT_PERSONA },
    { role: "user", content: userPrompt },
  ]);
  if (outQwen) {
    logUsage("summarize", Date.now() - start, QWEN_MODEL);
    return outQwen;
  }
  const client = getClient();
  if (client) {
    try {
      const model = client.getGenerativeModel({ model: GEMINI_MODEL });
      const result = await model.generateContent(`${AGENT_PERSONA}\n\n${userPrompt}`);
      const out = result.response.text?.()?.trim();
      if (out) {
        logUsage("summarize", Date.now() - start, GEMINI_MODEL);
        return out;
      }
    } catch (_) {}
  }
  return fallbackSummary(text, detailLevel);
}

export async function generateFlashcards(text: string, maxCards: number): Promise<Array<{ question: string; answer: string; explanation?: string }>> {
  const start = Date.now();
  const userPrompt = `Generate a JSON array of flashcards. Each object must have keys: question, answer, explanation. Return exactly ${maxCards} cards. No other text.\n\n${text.slice(0, 12000)}`;
  const rawQwen = await qwenComplete([{ role: "user", content: userPrompt }]);
  if (rawQwen) {
    const parsed = extractJsonArray(rawQwen);
    if (parsed.length) {
      logUsage("generate-flashcards", Date.now() - start, QWEN_MODEL);
      return parsed.slice(0, maxCards).map((o: Record<string, unknown>) => ({
        question: String(o.question ?? ""),
        answer: String(o.answer ?? ""),
        explanation: o.explanation != null ? String(o.explanation) : undefined,
      }));
    }
  }
  const client = getClient();
  if (client) {
    try {
      const model = client.getGenerativeModel({ model: GEMINI_MODEL });
      const result = await model.generateContent(userPrompt);
      const raw = result.response.text?.() ?? "";
      const parsed = extractJsonArray(raw);
      if (parsed.length) {
        logUsage("generate-flashcards", Date.now() - start, GEMINI_MODEL);
        return parsed.slice(0, maxCards).map((o: Record<string, unknown>) => ({
          question: String(o.question ?? ""),
          answer: String(o.answer ?? ""),
          explanation: o.explanation != null ? String(o.explanation) : undefined,
        }));
      }
    } catch (_) {}
  }
  return fallbackFlashcards(text, maxCards);
}

export async function chat(
  prompt: string,
  context: string[],
  attachmentDocTitle?: string | null
): Promise<string> {
  const start = Date.now();
  const contextBlock = context.slice(0, 14).join("\n\n");
  const attachmentHint =
    attachmentDocTitle && context.length > 0
      ? `The user has selected the document "${attachmentDocTitle}" as context. The following excerpts are from that document. Base your answer on this content and cite it when relevant.\n\n`
      : "";
  const contextLabel = attachmentDocTitle ? "Content from the attached/selected document:" : "Context (from user's documents):";
  const fullPrompt = `${AGENT_PERSONA}

${attachmentHint}${contextLabel}
${contextBlock}

User question:
${prompt}

Reply in character: be accurate and helpful, and keep the tone lovely, cute, and encouraging.`;

  const userContent = `${attachmentHint}${contextLabel}\n${contextBlock}\n\nUser question:\n${prompt}\n\nReply in character: be accurate and helpful, and keep the tone lovely, cute, and encouraging.`;
  const outQwen = await qwenComplete([
    { role: "system", content: AGENT_PERSONA },
    { role: "user", content: userContent },
  ]);
  if (outQwen) {
    logUsage("chat", Date.now() - start, QWEN_MODEL);
    return outQwen;
  }
  const client = getClient();
  if (client) {
    try {
      const model = client.getGenerativeModel({ model: GEMINI_MODEL });
      const result = await model.generateContent(fullPrompt);
      const out = result.response.text?.()?.trim();
      if (out) {
        logUsage("chat", Date.now() - start, GEMINI_MODEL);
        return out;
      }
    } catch (_) {}
  }
  return fallbackChat(prompt, context);
}

export interface DocSummaryForOrganize {
  title: string;
  topicHint?: string | null;
  summary: string;
}

/** Agent suggests how to organize course materials: study order, topics, and how they relate. */
export async function organizeMaterials(docSummaries: DocSummaryForOrganize[]): Promise<string> {
  if (!docSummaries.length) {
    return "还没有上传任何课程材料哦～先上传 PDF 或 TXT，我再帮你整理～";
  }
  const start = Date.now();
  const client = getClient();
  const materialsList = docSummaries
    .map(
      (d) =>
        `- **${d.title}**${d.topicHint ? `（${d.topicHint}）` : ""}\n  ${d.summary.slice(0, 500)}${d.summary.length > 500 ? "…" : ""}`
    )
    .join("\n\n");

  const prompt = `${AGENT_PERSONA}

用户上传了以下课程材料，请用温暖、有条理的方式帮他「整理」：

${materialsList}

请用简洁的中文回复，包含：
1) **建议学习顺序**：按什么顺序看这些材料更合理；
2) **主题/知识点**：这些材料主要涉及哪些主题；
3) **关联与重点**：材料之间有什么关系、建议重点看哪里。

保持可爱助教人设，不要啰嗦。`;

  const outQwen = await qwenComplete([
    { role: "system", content: AGENT_PERSONA },
    { role: "user", content: prompt },
  ]);
  if (outQwen) {
    logUsage("organize-materials", Date.now() - start, QWEN_MODEL);
    return outQwen;
  }
  if (client) {
    try {
      const model = client.getGenerativeModel({ model: GEMINI_MODEL });
      const result = await model.generateContent(prompt);
      const out = result.response.text?.()?.trim();
      if (out) {
        logUsage("organize-materials", Date.now() - start, GEMINI_MODEL);
        return out;
      }
    } catch (_) {}
  }
  return fallbackOrganize(docSummaries);
}

function fallbackOrganize(docSummaries: DocSummaryForOrganize[]): string {
  const order = docSummaries.map((d, i) => `${i + 1}. ${d.title}`).join("\n");
  return `**建议学习顺序**\n${order}\n\n**提示**：已根据标题列出顺序，你可以在聊天里问我「先学哪一份」或「这几份有什么关系」获得更详细的整理建议～`;
}

/** Result of classifying a document into a subject folder. */
export interface ClassifySubjectResult {
  subject_id: string | null;
  subject_name: string;
  is_new: boolean;
}

/**
 * Use LLM to classify a document into an existing subject or suggest a new one.
 * existingSubjects: list of { id, name }. Returns subject_id (if existing), subject_name, is_new.
 */
export async function classifySubjectForDocument(
  title: string,
  topicHint: string | null,
  textSnippet: string,
  existingSubjects: { id: string; name: string }[]
): Promise<ClassifySubjectResult> {
  const existingNames = existingSubjects.map((s) => s.name);
  const listText =
    existingNames.length > 0
      ? `Existing subject folders: ${existingNames.join(", ")}. Reply with one of these names if the document fits, otherwise reply NEW: <name> to create a new folder.`
      : "No subject folders yet. Reply NEW: <subject name> to create one (e.g. NEW: 线性代数).";
  const prompt = `You are classifying a document into a subject folder for a study app.

Document title: ${title}
${topicHint ? `Topic hint: ${topicHint}` : ""}

Document content snippet (first ~800 chars):
${textSnippet.slice(0, 800)}

${listText}
Reply with exactly one line: either an existing subject name, or "NEW: <subject name>" (no extra text).`;

  const out = await qwenComplete([{ role: "user", content: prompt }]);
  if (!out || !out.trim()) {
    const fallback = existingSubjects[0]
      ? { subject_id: existingSubjects[0].id, subject_name: existingSubjects[0].name, is_new: false }
      : { subject_id: null, subject_name: title.slice(0, 30), is_new: true };
    return fallback;
  }
  const line = out.trim().split("\n")[0].trim();
  const newMatch = line.match(/^NEW:\s*(.+)$/i);
  if (newMatch) {
    return { subject_id: null, subject_name: newMatch[1].trim(), is_new: true };
  }
  const name = line;
  const found = existingSubjects.find((s) => s.name.toLowerCase() === name.toLowerCase());
  if (found) {
    return { subject_id: found.id, subject_name: found.name, is_new: false };
  }
  return { subject_id: null, subject_name: name, is_new: true };
}

export async function embed(texts: string[]): Promise<number[][]> {
  const client = getClient();
  if (client) {
    try {
      const model = client.getGenerativeModel({ model: GEMINI_EMBED_MODEL });
      const vectors: number[][] = [];
      for (const text of texts) {
        const result = await model.embedContent(text);
        const emb = (result as { embedding?: { values?: number[] } }).embedding?.values;
        if (emb) {
          vectors.push(padVector(emb.slice(0, EMBEDDING_DIM)));
        } else {
          vectors.push(deterministicEmbedding(text));
        }
      }
      if (vectors.length) return vectors;
    } catch (_) {}
  }
  return texts.map((t) => deterministicEmbedding(t));
}

function padVector(v: number[]): number[] {
  if (v.length >= EMBEDDING_DIM) return v.slice(0, EMBEDDING_DIM);
  return [...v, ...Array(EMBEDDING_DIM - v.length).fill(0)];
}

function deterministicEmbedding(text: string): number[] {
  const crypto = require("crypto");
  const h = crypto.createHash("sha256").update(text, "utf8").digest("hex").slice(0, 16);
  let seed = parseInt(h, 16);
  const values: number[] = [];
  for (let i = 0; i < EMBEDDING_DIM; i++) {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    values.push((seed / 0x7fffffff) * 2 - 1);
  }
  const norm = Math.sqrt(values.reduce((s, v) => s + v * v, 0)) || 1;
  return values.map((v) => v / norm);
}

function extractJsonArray(raw: string): Record<string, unknown>[] {
  try {
    const arr = JSON.parse(raw);
    if (Array.isArray(arr)) return arr.filter((x) => x && typeof x === "object");
  } catch (_) {}
  const match = raw.match(/\[[\s\S]*\]/);
  if (match) {
    try {
      const arr = JSON.parse(match[0]);
      if (Array.isArray(arr)) return arr.filter((x) => x && typeof x === "object");
    } catch (_) {}
  }
  return [];
}

function fallbackSummary(text: string, detailLevel: string): string {
  const sentences = text.trim().split(/(?<=[.!?])\s+/).filter(Boolean);
  const take = detailLevel === "short" ? 2 : detailLevel === "detailed" ? 8 : 4;
  const selected = sentences.slice(0, take);
  if (!selected.length) return text.slice(0, 800).trim();
  return selected.map((s) => `- ${s.trim()}`).join("\n");
}

function fallbackFlashcards(text: string, maxCards: number): Array<{ question: string; answer: string; explanation?: string }> {
  const lines = text.split(/[\n.!?]/).map((l) => l.trim()).filter((l) => l.split(/\s+/).length > 5);
  const cards: Array<{ question: string; answer: string; explanation?: string }> = [];
  for (let i = 0; i < Math.min(lines.length, maxCards); i++) {
    const line = lines[i];
    cards.push({
      question: `What is the key idea from statement ${i + 1}?`,
      answer: line.split(/\s+/).slice(0, 12).join(" "),
      explanation: line,
    });
  }
  if (!cards.length) {
    cards.push({
      question: "What is the main topic of this document?",
      answer: text.slice(0, 120),
      explanation: "Generated fallback card because source text was sparse.",
    });
  }
  return cards;
}

function fallbackChat(prompt: string, context: string[]): string {
  const prefix = context.slice(0, 3).map((c) => `- ${c.slice(0, 220)}`).join("\n");
  if (prefix) {
    return `Here's a focused answer based on your notes:\n${prefix}\n\nWhat you're asking: ${prompt}\nUse these points to review, and feel free to ask follow-up questions—we can go deeper together! ✨`;
  }
  return "I'd love to help with this~ Try uploading a document or asking for a summary or flashcards, and I'll give you content-specific guidance. You've got this! 💪";
}
