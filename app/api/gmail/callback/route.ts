import { NextRequest, NextResponse } from "next/server";
import { exchangeCodeForTokens, saveRefreshToken } from "@/lib/gmail";

/**
 * GET /api/gmail/callback?code=...
 * OAuth callback: exchange code for tokens and store refresh token.
 */
export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");
  if (!code) {
    return NextResponse.redirect(new URL("/", req.url));
  }

  const tokens = await exchangeCodeForTokens(code);
  if (!tokens) {
    return NextResponse.json(
      { error: "token_exchange_failed", message: "Could not get tokens" },
      { status: 400 }
    );
  }

  saveRefreshToken(tokens.refreshToken);
  const base = process.env.GMAIL_SUCCESS_URL || "/";
  const url = new URL(base, req.url);
  url.searchParams.set("gmail", "connected");
  return NextResponse.redirect(url.toString());
}
