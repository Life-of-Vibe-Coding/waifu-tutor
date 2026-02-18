import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChatPage } from "./features/chat/ChatPage";
import { GmailConnect } from "./GmailConnect";
import { PageBackground } from "./PageBackground";
import { TutorPane } from "./TutorPane";

export const AppShell = () => {
  const [showGmail, setShowGmail] = useState(false);

  // #region agent log
  useEffect(() => {
    if (typeof fetch === "function") {
      fetch("http://127.0.0.1:7247/ingest/e74e64de-c421-49b4-a147-afaab464f989", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "0d5b46" },
        body: JSON.stringify({
          sessionId: "0d5b46",
          runId: "layout",
          hypothesisId: "H1",
          location: "AppShell.tsx:mount",
          message: "Layout: left aside=TutorPane, right main=ChatPage",
          data: { hasLeftAside: true, hasRightMain: true, innerWidth: typeof window !== "undefined" ? window.innerWidth : null },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
    }
  }, []);
  // #endregion

  return (
    <div className="relative isolate h-screen w-full overflow-hidden bg-slate-50 text-slate-900">
      <PageBackground />

      {/* Main Layout Container */}
      <div className="absolute inset-0 z-10 flex flex-col items-center justify-center p-2 sm:p-4 md:p-6">
        <div className="flex h-full w-full max-w-7xl flex-col gap-4 md:flex-row">

          {/* Unified Layout Container */}
          <div className="relative flex h-full w-full flex-col overflow-hidden rounded-3xl md:flex-row">

            {/* Left Panel: Tutor (Live2D) */}
            <aside
              className="relative flex h-80 w-full shrink-0 flex-col overflow-hidden md:h-full md:w-80 lg:w-96"
              role="complementary"
              aria-label="Tutor Character"
            >
              <TutorPane />
            </aside>

            {/* Right Panel: Chat Interface */}
            <main
              className="relative flex min-w-0 flex-1 flex-col overflow-hidden rounded-3xl border border-white/40 bg-white/30 shadow-xl backdrop-blur-xl"
              role="main"
              aria-label="Chat Interface"
            >
              <ChatPage />
            </main>

          </div>

        </div>
      </div>

      {/* Floating Controls (Gmail, Settings) */}
      <div className="pointer-events-none absolute inset-0 z-20">
        <div className="pointer-events-auto absolute right-4 top-4 flex flex-col items-end gap-3 sm:right-6 sm:top-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowGmail((s) => !s)}
              className="group relative flex h-10 w-10 items-center justify-center rounded-full border border-white/50 bg-white/40 text-slate-600 shadow-sm backdrop-blur-sm transition hover:scale-105 hover:bg-white/60 hover:text-red-500"
              aria-label={showGmail ? "Close Gmail" : "Gmail settings"}
              aria-expanded={showGmail}
            >
              <svg className="h-5 w-5 transition-transform group-hover:rotate-12" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </button>
            {/* CompanionHud is already inside TutorPane */}
          </div>
          <AnimatePresence>
            {showGmail && (
              <motion.div
                className="w-80 origin-top-right rounded-2xl border border-white/50 bg-white/80 p-1 shadow-2xl backdrop-blur-xl"
                initial={{ opacity: 0, scale: 0.95, y: -10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <GmailConnect onClose={() => setShowGmail(false)} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
