import { NextRequest, NextResponse } from "next/server";
import { rewriteHtmlForFrame, stripReloadParams } from "@/lib/course-frame-rewrite";

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

export async function GET(req: NextRequest) {
  let url = req.nextUrl.searchParams.get("url");
  if (!url || typeof url !== "string") {
    return NextResponse.json({ code: "missing_url", message: "Query param url is required" }, { status: 400 });
  }
  url = stripReloadParams(url);

  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return NextResponse.json({ code: "invalid_url", message: "Invalid URL" }, { status: 400 });
  }
  if (!["http:", "https:"].includes(parsed.protocol)) {
    return NextResponse.json({ code: "invalid_url", message: "Only http(s) URLs allowed" }, { status: 400 });
  }

  try {
    const res = await fetch(url, {
      headers: { "User-Agent": UA },
      redirect: "follow",
      signal: AbortSignal.timeout(20000),
    });
    if (!res.ok) {
      return NextResponse.json(
        { code: "fetch_failed", message: `Upstream returned ${res.status}` },
        { status: 502 }
      );
    }
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.toLowerCase().includes("text/html")) {
      return NextResponse.json(
        { code: "not_html", message: "URL did not return HTML" },
        { status: 400 }
      );
    }
    const html = await res.text();
    const finalUrl = stripReloadParams(res.url || url);
    const rewritten = rewriteHtmlForFrame(html, finalUrl, "/api/school-proxy");

    return new NextResponse(rewritten, {
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "X-Frame-Options": "SAMEORIGIN",
      },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Proxy request failed";
    console.error("[school-proxy]", e);
    return NextResponse.json({ code: "proxy_error", message: msg }, { status: 502 });
  }
}
