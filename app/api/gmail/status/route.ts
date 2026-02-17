import { NextResponse } from "next/server";
import { getAccessToken, isGmailConfigured } from "@/lib/gmail";

/**
 * GET /api/gmail/status
 * Returns whether Gmail is configured and connected.
 */
export async function GET() {
  try {
    const configured = isGmailConfigured();
    const token = configured ? await getAccessToken() : null;
    return NextResponse.json({
      configured,
      connected: !!token,
    });
  } catch {
    return NextResponse.json({ configured: false, connected: false });
  }
}
