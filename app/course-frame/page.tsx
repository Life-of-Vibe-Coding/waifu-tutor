"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, useCallback } from "react";
import { rewriteHtmlForFrame, stripReloadParams } from "@/lib/course-frame-rewrite";

type Status = "idle" | "loading" | "ok" | "error";

function CourseFrameContent() {
  const searchParams = useSearchParams();
  const url = searchParams.get("url");
  const [status, setStatus] = useState<Status>("idle");
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [finalUrl, setFinalUrl] = useState<string | null>(null);

  const framePath = "/course-frame";

  const load = useCallback(async (targetUrl: string) => {
    const stableUrl = stripReloadParams(targetUrl);
    setStatus("loading");
    setError(null);
    setHtml(null);
    setFinalUrl(null);
    try {
      const res = await fetch(stableUrl, {
        method: "GET",
        credentials: "include",
        redirect: "follow",
        signal: AbortSignal.timeout(30000),
      });
      if (!res.ok) {
        setError(`HTTP ${res.status}`);
        setStatus("error");
        return;
      }
      const contentType = res.headers.get("content-type") || "";
      if (!contentType.toLowerCase().includes("text/html")) {
        setError("Response is not HTML");
        setStatus("error");
        return;
      }
      const text = await res.text();
      const resolvedUrl = stripReloadParams(res.url || stableUrl);
      const rewritten = rewriteHtmlForFrame(text, resolvedUrl, framePath);
      setHtml(rewritten);
      setFinalUrl(resolvedUrl);
      setStatus("ok");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Request failed";
      const isCors = msg.includes("CORS") || msg.includes("Failed to fetch") || msg.includes("NetworkError");
      setError(isCors ? "Site blocks embedding (CORS). Try opening the URL in a new tab and paste it for Get." : msg);
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    if (url && url.startsWith("http")) {
      load(url);
    } else {
      setStatus("idle");
      setError(url ? "Invalid URL" : null);
    }
  }, [url, load]);

  if (!url || !url.startsWith("http")) {
    return (
      <div className="flex h-full min-h-[120px] items-center justify-center bg-slate-100 p-4 text-slate-600">
        No URL provided. Open from the course fetch dialog.
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="flex h-full min-h-[120px] items-center justify-center bg-slate-100 p-4">
        <span className="text-slate-600">Loading… (using your browser cookies)</span>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex h-full min-h-[120px] flex-col items-center justify-center gap-2 bg-slate-100 p-4 text-slate-700">
        <p className="font-medium">Could not load page</p>
        <p className="text-center text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (status === "ok" && html) {
    return (
      <iframe
        srcDoc={html}
        title="Course content"
        className="h-full w-full border-0"
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-top-navigation-by-user-activation"
      />
    );
  }

  return null;
}

export default function CourseFramePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-full min-h-[200px] items-center justify-center bg-slate-100 p-4 text-slate-600">
          Loading…
        </div>
      }
    >
      <CourseFrameContent />
    </Suspense>
  );
}
