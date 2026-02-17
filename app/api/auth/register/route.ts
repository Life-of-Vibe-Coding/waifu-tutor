import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { DEMO_USER_ID } from "@/lib/constants";

function issueToken(userId: string): string {
  const payload = JSON.stringify({
    sub: userId,
    exp: Math.floor(Date.now() / 1000) + 24 * 60 * 60,
  });
  return `demo.${Buffer.from(payload, "utf8").toString("base64url")}.token`;
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { email, password } = body;
  if (!email || !password) {
    return NextResponse.json(
      { code: "invalid_request", message: "Invalid registration payload" },
      { status: 400 }
    );
  }
  const db = getDb();
  const user = db.prepare("SELECT id, email, display_name FROM users WHERE id = ?").get(DEMO_USER_ID) as { id: string; email: string; display_name: string } | undefined;
  if (!user) {
    return NextResponse.json(
      { code: "invalid_request", message: "Invalid registration payload" },
      { status: 400 }
    );
  }
  return NextResponse.json({
    access_token: issueToken(user.id),
    token_type: "bearer",
    profile: { id: user.id, email: user.email, display_name: user.display_name },
  });
}
