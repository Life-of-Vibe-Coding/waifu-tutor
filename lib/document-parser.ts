import fs from "fs";
import path from "path";

export function chunkText(text: string, chunkSize = 700, overlap = 120): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const chunks: string[] = [];
  let start = 0;
  while (start < words.length) {
    const end = Math.min(start + chunkSize, words.length);
    const chunk = words.slice(start, end).join(" ").trim();
    if (chunk) chunks.push(chunk);
    if (end >= words.length) break;
    start = Math.max(0, end - overlap);
  }
  return chunks;
}

export function topKeywords(text: string, maxKeywords = 5): string[] {
  const stop = new Set(["the", "a", "an", "is", "of", "for", "and", "to", "in", "on", "with", "that", "it", "this", "as"]);
  const freq: Record<string, number> = {};
  for (const raw of text.toLowerCase().split(/\s+/)) {
    const token = raw.replace(/\W/g, "");
    if (token.length < 4 || stop.has(token)) continue;
    freq[token] = (freq[token] ?? 0) + 1;
  }
  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, maxKeywords)
    .map(([t]) => t);
}

export function estimateDifficulty(wordCount: number): string {
  if (wordCount < 500) return "easy";
  if (wordCount < 2000) return "medium";
  return "hard";
}

export async function parseDocument(filePath: string): Promise<string> {
  const ext = path.extname(filePath).toLowerCase();
  const buf = fs.readFileSync(filePath);

  if ([".txt", ".md"].includes(ext)) {
    return buf.toString("utf8").replace(/\r\n/g, "\n");
  }

  if (ext === ".pdf") {
    const pdfParse = (await import("pdf-parse")).default;
    const data = await pdfParse(buf);
    return (data as { text: string }).text?.trim() ?? "";
  }

  if (ext === ".docx") {
    const mammoth = await import("mammoth");
    const result = await mammoth.extractRawText({ buffer: buf });
    return result.value?.trim() ?? "";
  }

  throw new Error(`Unsupported file type: ${ext}`);
}
