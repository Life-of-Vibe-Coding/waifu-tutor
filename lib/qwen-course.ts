/**
 * Fetch course materials from a URL using Qwen (DashScope) API.
 * Fetches the page, extracts text, and uses Qwen to extract/organize course content.
 */

const DASHSCOPE_API_KEY = process.env.DASHSCOPE_API_KEY;
const DASHSCOPE_BASE = process.env.DASHSCOPE_BASE || "https://dashscope-intl.aliyuncs.com";
const QWEN_MODEL = process.env.QWEN_MODEL || "qwen-plus";
// OpenAI-compatible endpoint (more reliable than native path)
const CHAT_URL = `${DASHSCOPE_BASE}/compatible-mode/v1/chat/completions`;

function stripHtmlToText(html: string): string {
  const noScript = html.replace(/<script[\s\S]*?<\/script>/gi, "");
  const noStyle = noScript.replace(/<style[\s\S]*?<\/style>/gi, "");
  const text = noStyle
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .trim();
  return text.slice(0, 60000);
}

async function callQwen(prompt: string): Promise<string> {
  if (!DASHSCOPE_API_KEY) {
    throw new Error("DASHSCOPE_API_KEY is not set. Add it to .env for Qwen course fetch.");
  }
  const res = await fetch(CHAT_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${DASHSCOPE_API_KEY}`,
    },
    body: JSON.stringify({
      model: QWEN_MODEL,
      messages: [{ role: "user", content: prompt }],
    }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Qwen API error ${res.status}: ${err.slice(0, 300)}`);
  }
  const data = (await res.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
    output?: { choices?: Array<{ message?: { content?: string } }> };
  };
  const content =
    data.choices?.[0]?.message?.content?.trim() ??
    data.output?.choices?.[0]?.message?.content?.trim();
  if (!content) {
    throw new Error("Qwen API returned empty content");
  }
  return content;
}

export async function fetchCourseWithQwen(pageUrl: string): Promise<string> {
  const res = await fetch(pageUrl, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    },
    redirect: "follow",
    signal: AbortSignal.timeout(30000),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch URL: ${res.status} ${res.statusText}`);
  }
  const html = await res.text();
  const rawText = stripHtmlToText(html);
  if (!rawText || rawText.length < 50) {
    throw new Error(
      "This page requires login. Server-side fetch cannot use your session. Try a public course URL, or copy-paste the content into a document and upload."
    );
  }

  const prompt = `You are helping extract course/learning materials from a webpage.

Raw webpage text (may be messy):
---
${rawText}
---

Extract and organize the course materials: main topics, key concepts, important content, and structure. Output as clean, readable markdown. Preserve headings, lists, and important details. If this appears to be a login page or has little course content, say "No course content found - the page may require login."`;
  return callQwen(prompt);
}
