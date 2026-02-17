import { NextRequest, NextResponse } from "next/server";
import {
  getAccessToken,
  listMessages,
  getMessage,
} from "@/lib/gmail";

/**
 * GET /api/gmail/mail?maxResults=25&q=...&id=...
 * List inbox messages or fetch a single message by id.
 */
export async function GET(req: NextRequest) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: "not_connected", message: "Connect Gmail first" },
      { status: 401 }
    );
  }

  const { searchParams } = req.nextUrl;
  const id = searchParams.get("id");

  try {
    if (id) {
      const msg = await getMessage(token, id);
      return NextResponse.json(msg ? { message: msg } : { error: "not_found" });
    }

    const maxResults = Math.min(100, Math.max(1, parseInt(searchParams.get("maxResults") ?? "25", 10) || 25));
    const q = searchParams.get("q") ?? undefined;
    const pageToken = searchParams.get("pageToken") ?? undefined;

    const result = await listMessages(token, { maxResults, q, pageToken });
    return NextResponse.json({
      messages: result.messages ?? [],
      resultSizeEstimate: result.resultSizeEstimate,
      nextPageToken: result.nextPageToken,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { error: "gmail_error", message: msg },
      { status: 502 }
    );
  }
}
