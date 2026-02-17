import { NextResponse } from "next/server";
import { getGmailLoginUrl } from "@/lib/gmail";

/**
 * GET /api/gmail/auth
 * Returns the Google login URL. Frontend redirects user there to connect Gmail.
 */
export async function GET() {
  const loginUrl = getGmailLoginUrl();
  if (!loginUrl) {
    return NextResponse.json(
      {
        error: "gmail_not_configured",
        message:
          "Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REDIRECT_URI in .env",
      },
      { status: 501 }
    );
  }
  return NextResponse.json({ loginUrl });
}
