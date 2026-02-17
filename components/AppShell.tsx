"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChatPage } from "./features/chat/ChatPage";
import { NotesPage } from "./features/notes/NotesPage";
import { CompanionHud } from "./cute/CompanionHud";
import { GmailConnect } from "./GmailConnect";
import { PageBackground } from "./PageBackground";
import { TutorPane } from "./TutorPane";
import { useAppStore } from "@/state/appStore";

function MainViewTabs() {
  const mainView = useAppStore((s) => s.mainView);
  const setMainView = useAppStore((s) => s.setMainView);
  return (
    <div className="flex shrink-0 border-b border-white/50 bg-white/25 px-3 py-1.5 backdrop-blur-sm">
      <div className="flex rounded-full border border-white/60 bg-white/40 p-0.5">
        <button
          type="button"
          onClick={() => setMainView("chat")}
          className={`rounded-full px-4 py-1.5 text-sm font-bold transition ${
            mainView === "chat" ? "bg-sakura/50 text-ink shadow-sm" : "text-slate-600 hover:bg-white/60"
          }`}
        >
          对话
        </button>
        <button
          type="button"
          onClick={() => setMainView("notes")}
          className={`rounded-full px-4 py-1.5 text-sm font-bold transition ${
            mainView === "notes" ? "bg-aqua/50 text-ink shadow-sm" : "text-slate-600 hover:bg-white/60"
          }`}
        >
          学习笔记
        </button>
      </div>
    </div>
  );
}

export const AppShell = () => {
  const [showGmail, setShowGmail] = useState(false);
  const mainView = useAppStore((s) => s.mainView);

  return (
    <div className="relative isolate h-screen overflow-hidden">
      <PageBackground />
      <div className="absolute inset-0 z-10 flex items-stretch justify-center px-2 pb-2 pt-0 sm:px-3 sm:pb-3">
        <main
          className="flex h-full min-h-0 w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-white/65 bg-white/35 shadow-[0_34px_90px_rgba(66,76,128,0.28)] backdrop-blur-md sm:flex-row sm:rounded-3xl"
          role="application"
          aria-label="Waifu Tutor"
        >
          <TutorPane />
          <div className="relative flex min-w-0 flex-1 flex-col">
            <MainViewTabs />
            {mainView === "chat" ? <ChatPage /> : <NotesPage />}
          </div>
        </main>
      </div>
      <div className="pointer-events-none absolute inset-0 z-20">
        <div className="pointer-events-auto absolute right-3 top-3 flex flex-col items-end gap-2 sm:right-6 sm:top-6">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowGmail((s) => !s)}
              className="rounded-full p-2 text-slate-600 transition hover:bg-white/50 hover:text-red-600"
              aria-label={showGmail ? "Close Gmail" : "Gmail settings"}
              aria-expanded={showGmail}
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </button>
            <CompanionHud />
          </div>
          <AnimatePresence>
            {showGmail && (
              <motion.div
                className="w-72 sm:w-80"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
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
