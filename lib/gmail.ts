/**
 * Google Gmail API integration.
 * OAuth 2.0 Authorization Code flow.
 * Supports: read inbox, send mail.
 */

import fs from "fs";
import path from "path";

const GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me";
const AUTH_BASE = "https://accounts.google.com";
const TOKEN_FILE =
  process.env.GMAIL_TOKEN_FILE || path.join(process.cwd(), "data", "gmail_refresh_token.txt");
const SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/userinfo.email",
];

export interface GmailConfig {
  clientId: string;
  clientSecret: string;
  redirectUri: string;
}

export interface GmailMessage {
  id: string;
  threadId: string;
  labelIds?: string[];
  snippet?: string;
  internalDate?: string;
  payload?: {
    headers?: Array<{ name: string; value: string }>;
  };
}

function getConfig(): GmailConfig | null {
  const clientId = process.env.GMAIL_CLIENT_ID;
  const clientSecret = process.env.GMAIL_CLIENT_SECRET;
  const redirectUri = process.env.GMAIL_REDIRECT_URI;
  if (!clientId || !clientSecret || !redirectUri) return null;
  return { clientId, clientSecret, redirectUri };
}

export function isGmailConfigured(): boolean {
  return getConfig() !== null;
}

export function saveRefreshToken(refreshToken: string): void {
  const dir = path.dirname(TOKEN_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(TOKEN_FILE, refreshToken.trim(), "utf8");
}

export function getStoredRefreshToken(): string | null {
  const fromEnv = process.env.GMAIL_REFRESH_TOKEN?.trim();
  if (fromEnv) return fromEnv;
  try {
    if (fs.existsSync(TOKEN_FILE))
      return fs.readFileSync(TOKEN_FILE, "utf8").trim() || null;
  } catch (_) {}
  return null;
}

export function getGmailLoginUrl(): string | null {
  const config = getConfig();
  if (!config) return null;
  const params = new URLSearchParams({
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    response_type: "code",
    scope: SCOPES.join(" "),
    access_type: "offline",
    prompt: "consent",
  });
  return `${AUTH_BASE}/o/oauth2/v2/auth?${params.toString()}`;
}

export async function exchangeCodeForTokens(
  code: string
): Promise<{ accessToken: string; refreshToken: string; expiresIn: number } | null> {
  const config = getConfig();
  if (!config) return null;

  const body = new URLSearchParams({
    client_id: config.clientId,
    client_secret: config.clientSecret,
    code,
    redirect_uri: config.redirectUri,
    grant_type: "authorization_code",
  });

  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error("[gmail] token exchange failed:", res.status, err);
    return null;
  }

  const data = (await res.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  };
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    expiresIn: data.expires_in,
  };
}

export async function getAccessTokenFromRefresh(
  refreshToken: string
): Promise<string | null> {
  const config = getConfig();
  if (!config) return null;

  const body = new URLSearchParams({
    client_id: config.clientId,
    client_secret: config.clientSecret,
    refresh_token: refreshToken,
    grant_type: "refresh_token",
  });

  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error("[gmail] refresh failed:", res.status, err);
    return null;
  }

  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export async function getAccessToken(): Promise<string | null> {
  const refresh = getStoredRefreshToken();
  if (!refresh) return null;
  return getAccessTokenFromRefresh(refresh);
}

export interface ListMessagesResult {
  messages: Array<{ id: string; threadId: string }>;
  resultSizeEstimate?: number;
  nextPageToken?: string;
}

export async function listMessages(
  accessToken: string,
  options: { maxResults?: number; q?: string; pageToken?: string } = {}
): Promise<ListMessagesResult> {
  const { maxResults = 25, q, pageToken } = options;
  const url = new URL(`${GMAIL_API}/messages`);
  url.searchParams.set("maxResults", String(Math.min(100, maxResults)));
  if (q) url.searchParams.set("q", q);
  if (pageToken) url.searchParams.set("pageToken", pageToken);

  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    const err = await res.text();
    console.error("[gmail] list messages failed:", res.status, err);
    throw new Error(`Gmail API error: ${res.status}`);
  }

  const data = (await res.json()) as ListMessagesResult;
  return data;
}

export interface MessageDetail {
  id: string;
  threadId: string;
  snippet?: string;
  subject?: string;
  from?: string;
  to?: string;
  date?: string;
}

export async function getMessage(
  accessToken: string,
  messageId: string
): Promise<MessageDetail | null> {
  const res = await fetch(`${GMAIL_API}/messages/${messageId}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Date`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    if (res.status === 404) return null;
    const err = await res.text();
    console.error("[gmail] get message failed:", res.status, err);
    throw new Error(`Gmail API error: ${res.status}`);
  }

  const data = (await res.json()) as GmailMessage;
  const headers = data.payload?.headers ?? [];
  const getHeader = (name: string) =>
    headers.find((h) => h.name.toLowerCase() === name.toLowerCase())?.value ?? "";

  return {
    id: data.id,
    threadId: data.threadId ?? "",
    snippet: data.snippet,
    subject: getHeader("Subject"),
    from: getHeader("From"),
    to: getHeader("To"),
    date: getHeader("Date"),
  };
}

export interface SendMailOptions {
  to: string | string[];
  subject: string;
  body: string;
  bodyIsHtml?: boolean;
}

function createRawMessage(options: SendMailOptions): string {
  const to = Array.isArray(options.to) ? options.to : [options.to];
  const lines = [
    `To: ${to.join(", ")}`,
    `Subject: ${options.subject}`,
    "MIME-Version: 1.0",
    options.bodyIsHtml
      ? "Content-Type: text/html; charset=utf-8"
      : "Content-Type: text/plain; charset=utf-8",
    "",
    options.body,
  ];
  return Buffer.from(lines.join("\r\n")).toString("base64url");
}

export async function sendMail(
  accessToken: string,
  options: SendMailOptions
): Promise<void> {
  const raw = createRawMessage(options);
  const res = await fetch(`${GMAIL_API}/messages/send`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ raw }),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error("[gmail] send mail failed:", res.status, err);
    throw new Error(`Gmail API error: ${res.status}`);
  }
}
