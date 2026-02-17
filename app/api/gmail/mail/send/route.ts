import { NextRequest, NextResponse } from "next/server";
import { getAccessToken, sendMail } from "@/lib/gmail";

/**
 * POST /api/gmail/mail/send
 * Body: { to, subject, body, bodyIsHtml? }
 */
export async function POST(req: NextRequest) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: "not_connected", message: "Connect Gmail first" },
      { status: 401 }
    );
  }

  const body = await req.json().catch(() => ({}));
  const { to, subject, body: emailBody } = body;

  if (!to || !subject || typeof emailBody !== "string") {
    return NextResponse.json(
      { error: "invalid_request", message: "to, subject, and body are required" },
      { status: 400 }
    );
  }

  try {
    await sendMail(token, {
      to: Array.isArray(to) ? to : [to],
      subject: String(subject).trim(),
      body: emailBody.trim(),
      bodyIsHtml: body.bodyIsHtml === true,
    });
    return NextResponse.json({ ok: true });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { error: "gmail_error", message: msg },
      { status: 502 }
    );
  }
}
