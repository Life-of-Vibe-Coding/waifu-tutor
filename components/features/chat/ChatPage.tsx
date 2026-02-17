"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { stripReloadParams } from "@/lib/course-frame-rewrite";
import type { FetchCourseRecordResponse } from "@/lib/endpoints";
import { chat, fetchCourse, listDocuments, listSubjects, streamChat, uploadDocument, organizeMaterials, confirmDocumentSubject } from "@/lib/endpoints";
import { speakText } from "@/lib/tts";
import { useAppStore } from "@/state/appStore";
import type { CharacterMood, ChatMessage, CompanionStatus, DocumentMeta } from "@/types/domain";

const moodLabel: Record<CharacterMood, string> = {
  neutral: "Calm Focus",
  happy: "Sparkly Happy",
  encouraging: "Cheering You On",
  sad: "Soft Comfort",
  excited: "High Energy",
};

const bubbleTone: Record<ChatMessage["role"], string> = {
  user: "ml-auto border-sakura/70 bg-sakura/35 text-slate-900",
  assistant: "mr-auto border-aqua/70 bg-aqua/32 text-slate-900",
  system: "mx-auto border-butter/70 bg-butter/38 text-slate-700",
};

export const ChatPage = () => {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);
  const [sparkleBursts, setSparkleBursts] = useState<number[]>([]);
  const [showCourseFetch, setShowCourseFetch] = useState(false);
  const [courseUrl, setCourseUrl] = useState("https://ntulearn.ntu.edu.sg/ultra/courses/_2701247_1/outline");
  const [iframeSrc, setIframeSrc] = useState<string | null>(null);
  const [pastedUrlForGet, setPastedUrlForGet] = useState("");
  const schoolIframeRef = useRef<HTMLIFrameElement | null>(null);
  const [showOrganize, setShowOrganize] = useState(false);
  const [organizeResult, setOrganizeResult] = useState<string | null>(null);
  const [subjectConfirmPending, setSubjectConfirmPending] = useState<{
    docId: string;
    docTitle: string;
    suggestedSubjectId: string;
    suggestedSubjectName: string;
  } | null>(null);

  const activeDocId = useAppStore((s) => s.activeDocId);
  const setActiveDocId = useAppStore((s) => s.setActiveDocId);
  const mood = useAppStore((s) => s.mood);
  const ttsEnabled = useAppStore((s) => s.ttsEnabled);
  const toggleTts = useAppStore((s) => s.toggleTts);
  const messages = useAppStore((s) => s.messages);
  const setMessages = useAppStore((s) => s.setMessages);
  const setMood = useAppStore((s) => s.setMood);
  const isListening = useAppStore((s) => s.isListening);
  const setListening = useAppStore((s) => s.setListening);
  const companionStatus = useAppStore((s) => s.companionStatus);
  const setCompanionStatus = useAppStore((s) => s.setCompanionStatus);
  const bumpAffection = useAppStore((s) => s.bumpAffection);
  const incrementSessionStreak = useAppStore((s) => s.incrementSessionStreak);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const messagesScrollContainerRef = useRef<HTMLDivElement | null>(null);
  const lastScrolledMessageCountRef = useRef(0);
  const celebrationTimeoutRef = useRef<number | ReturnType<typeof setTimeout> | null>(null);
  const sparkleIdRef = useRef(0);
  const sparkleTimersRef = useRef<Array<number | ReturnType<typeof setTimeout>>>([]);

  const docsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const readyDocs = useMemo(() => docsQuery.data?.filter((d) => d.status === "ready") ?? [], [docsQuery.data]);

  const triggerCelebration = () => {
    if (celebrationTimeoutRef.current) window.clearTimeout(celebrationTimeoutRef.current);
    setCompanionStatus("celebrating");
    celebrationTimeoutRef.current = window.setTimeout(() => setCompanionStatus("idle"), 1200);
  };

  const triggerSparkleTrail = () => {
    const id = sparkleIdRef.current + 1;
    sparkleIdRef.current = id;
    setSparkleBursts((prev) => [...prev, id]);
    const timer = window.setTimeout(() => {
      setSparkleBursts((prev) => prev.filter((x) => x !== id));
      sparkleTimersRef.current = sparkleTimersRef.current.filter((t) => t !== timer);
    }, 900);
    sparkleTimersRef.current.push(timer);
  };

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async (doc) => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      setActiveDocId(doc.id);
      setMood("excited");
      bumpAffection(2);
      const meta = doc as DocumentMeta & { subject_needs_confirmation?: boolean; suggested_subject_id?: string; suggested_subject_name?: string };
      if (meta.subject_needs_confirmation && meta.suggested_subject_id && meta.suggested_subject_name) {
        setSubjectConfirmPending({
          docId: doc.id,
          docTitle: doc.title,
          suggestedSubjectId: meta.suggested_subject_id,
          suggestedSubjectName: meta.suggested_subject_name,
        });
        setUploadNotice(`Uploaded ${doc.title}. Is it for subject 「${meta.suggested_subject_name}」? Confirm below.`);
      } else {
        setUploadNotice(`Uploaded ${doc.title} and selected it as context.`);
      }
      triggerCelebration();
    },
    onError: () => {
      setMood("sad");
      setCompanionStatus("comforting");
      setUploadNotice("Upload failed. Please try another document.");
    },
  });

  const confirmSubjectMutation = useMutation({
    mutationFn: ({ docId, subjectId }: { docId: string; subjectId: string }) =>
      confirmDocumentSubject(docId, subjectId),
    onSuccess: async () => {
      setSubjectConfirmPending(null);
      setUploadNotice(null);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      await queryClient.invalidateQueries({ queryKey: ["subjects"] });
    },
    onError: () => {
      setSubjectConfirmPending(null);
    },
  });

  const organizeMutation = useMutation({
    mutationFn: () => organizeMaterials(),
    onSuccess: (data) => {
      setOrganizeResult(data.organization);
      setShowOrganize(true);
      setMood("happy");
    },
    onError: () => {
      setMood("sad");
      setOrganizeResult("整理失败，请稍后再试～");
      setShowOrganize(true);
    },
  });

  const fetchCourseMutation = useMutation({
    mutationFn: fetchCourse,
    onSuccess: async (data) => {
      const recordResp = data as FetchCourseRecordResponse;
      if (recordResp?.recorded === true) {
        setUploadNotice(recordResp.message);
        setMood("happy");
        return;
      }
      const doc = data as { id: string; title: string };
      setShowCourseFetch(false);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      setActiveDocId(doc.id);
      setMood("excited");
      bumpAffection(2);
      setUploadNotice(`Fetched course: ${doc.title}. Selected as context.`);
      triggerCelebration();
    },
    onError: (err: unknown) => {
      setMood("sad");
      setCompanionStatus("comforting");
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        (err instanceof Error ? err.message : "Course fetch failed.");
      setUploadNotice(msg);
    },
  });

  useEffect(() => {
    const newCount = messages.length;
    const prevCount = lastScrolledMessageCountRef.current;
    if (newCount > prevCount && messagesEndRef.current && messagesScrollContainerRef.current) {
      lastScrolledMessageCountRef.current = newCount;
      const el = messagesScrollContainerRef.current;
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    } else if (newCount !== prevCount) {
      lastScrolledMessageCountRef.current = newCount;
    }
  }, [messages]);
  useEffect(() => {
    const typing = input.trim().length > 0;
    setListening(loading || typing);
    if (loading && companionStatus !== "celebrating") { setCompanionStatus("thinking"); return; }
    if (typing && companionStatus !== "celebrating") { setCompanionStatus("listening"); return; }
    if (!typing && !loading && companionStatus === "listening") setCompanionStatus("idle");
  }, [input, loading, companionStatus, setCompanionStatus, setListening]);
  useEffect(() => () => {
    setListening(false);
    if (celebrationTimeoutRef.current) window.clearTimeout(celebrationTimeoutRef.current);
    sparkleTimersRef.current.forEach((t) => window.clearTimeout(t));
    sparkleTimersRef.current = [];
  }, [setListening]);

  const send = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);
    setError(null);
    setCompanionStatus("thinking");
    bumpAffection(2);
    incrementSessionStreak();
    triggerSparkleTrail();
    const userMessage: ChatMessage = { role: "user", content: input.trim() };
    const history = [...messages, userMessage];
    setMessages([...history, { role: "assistant", content: "" }]);
    setInput("");
    let assistantText = "";
    try {
      await streamChat(userMessage.content, history, activeDocId, (event) => {
        if (event.type === "token") {
          const token = (event.payload as { token?: string })?.token;
          assistantText = `${assistantText} ${String(token ?? "")}`.trim();
          setMessages([...history, { role: "assistant", content: assistantText }]);
        }
        if (event.type === "mood" && (event.payload as { mood?: string })?.mood) {
          setMood((event.payload as { mood: CharacterMood }).mood);
        }
        if (event.type === "done") {
          const finalMessage = String((event.payload as { message?: string })?.message ?? assistantText);
          setMessages([...history, { role: "assistant", content: finalMessage }]);
          if (ttsEnabled) speakText(finalMessage);
          bumpAffection(3);
          setMood("encouraging");
          triggerCelebration();
        }
      });
    } catch {
      try {
        const response = await chat(userMessage.content, history, activeDocId);
        setMessages([...history, response.message]);
        setMood(response.mood);
        if (ttsEnabled) speakText(response.message.content);
        bumpAffection(3);
        triggerCelebration();
      } catch {
        setError("Failed to get response from assistant.");
        setMood("sad");
        setCompanionStatus("comforting");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelection = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.type.startsWith("video/") || /\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(file.name)) {
      setUploadNotice("暂不支持视频。请上传课程材料：PDF、TXT、DOCX 或 MD。");
      setCompanionStatus("comforting");
      return;
    }
    if (!/\.(pdf|docx|txt|md)$/i.test(file.name)) {
      setUploadNotice("请上传课程材料：PDF、TXT、DOCX 或 MD。");
      setCompanionStatus("comforting");
      return;
    }
    setUploadNotice(null);
    uploadMutation.mutate(file);
  };

  return (
    <section className="flex h-full flex-col overflow-hidden">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-white/50 bg-white/30 px-4 py-3 backdrop-blur-sm sm:px-5">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-display text-xl font-bold tracking-tight text-ink sm:text-2xl">Waifu Tutor</h1>
            <span className="rounded-full border border-white/75 bg-white/55 px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-sm" title="Companion mood">
              {moodLabel[mood]}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5">
              <label htmlFor="context-select" className="sr-only">当前对话使用的文档</label>
              <select
                id="context-select"
                value={activeDocId ?? ""}
                onChange={(e) => setActiveDocId(e.target.value || null)}
                className="rounded-full border border-white/80 bg-white/62 px-3 py-2 text-sm font-semibold text-slate-800 shadow-soft focus:outline-none focus:ring-2 focus:ring-sakura/80"
                aria-describedby={!activeDocId ? "context-hint" : undefined}
              >
                <option value="">未选择文档</option>
                {readyDocs.map((doc) => (
                  <option key={doc.id} value={doc.id}>{doc.title}</option>
                ))}
              </select>
              {!activeDocId && !docsQuery.isLoading && (
                <span id="context-hint" className="hidden text-xs text-slate-600 sm:inline">可选</span>
              )}
            </div>
            <button
              type="button"
              disabled={readyDocs.length === 0 || organizeMutation.isPending}
              onClick={() => organizeMutation.mutate()}
              className="shrink-0 rounded-full border border-white/85 bg-gradient-to-br from-violet-400/90 to-purple-500/90 px-3 py-2 text-sm font-semibold text-white shadow-md transition hover:scale-[1.02] disabled:opacity-50 disabled:hover:scale-100"
              aria-label="让助手整理课程材料"
              title="根据已上传的 PDF/TXT 等材料，生成学习顺序与重点建议"
            >
              {organizeMutation.isPending ? "整理中…" : "整理课程材料"}
            </button>
            <button
              type="button"
              onClick={toggleTts}
              aria-pressed={ttsEnabled}
              className={`rounded-full border px-3 py-2 text-sm font-bold transition ${ttsEnabled ? "border-aqua/90 bg-aqua/65 text-cyan-900" : "border-white/80 bg-white/42 text-slate-700"}`}
            >
              Voice {ttsEnabled ? "On" : "Off"}
            </button>
          </div>
      </header>

      {subjectConfirmPending && (
        <div className="mx-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-sakura/60 bg-sakura/25 px-4 py-2 sm:mx-4">
          <span className="text-sm font-semibold text-slate-800">
            Put 「{subjectConfirmPending.docTitle}」 in subject 【{subjectConfirmPending.suggestedSubjectName}】?
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={confirmSubjectMutation.isPending}
              onClick={() =>
                confirmSubjectMutation.mutate({
                  docId: subjectConfirmPending.docId,
                  subjectId: subjectConfirmPending.suggestedSubjectId,
                })
              }
              className="rounded-full border border-green-600/80 bg-green-500/90 px-3 py-1.5 text-sm font-bold text-white shadow-sm hover:bg-green-600/95 disabled:opacity-50"
            >
              {confirmSubjectMutation.isPending ? "…" : "Yes"}
            </button>
            <button
              type="button"
              disabled={confirmSubjectMutation.isPending}
              onClick={() => { setSubjectConfirmPending(null); setUploadNotice(null); }}
              className="rounded-full border border-white/80 bg-white/70 px-3 py-1.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-white/90"
            >
              No
            </button>
          </div>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col gap-2 p-3 sm:p-4">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-white/55 bg-white/20">
          <div
            ref={messagesScrollContainerRef}
            className="flex min-h-0 flex-1 flex-col space-y-3 overflow-y-auto rounded-xl border border-white/40 bg-white/14 px-3 py-4 sm:px-5"
          >
              {messages.length === 0 && (
                <motion.p
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass-bubble rounded-2xl px-4 py-3 text-sm font-semibold text-slate-700 text-glass"
                >
                  Ask a question to start. Your maid tutor is ready to help.
                </motion.p>
              )}
              <AnimatePresence initial={false}>
                {messages.map((msg, i) => (
                  <motion.div
                    key={`${msg.role}-${i}`}
                    initial={{ opacity: 0, y: 26, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8, scale: 0.92 }}
                    transition={{ type: "spring", stiffness: 250, damping: 22, mass: 0.7 }}
                    className={`glass-bubble max-w-[92%] rounded-[1.45rem] px-4 py-3 text-sm leading-relaxed ${bubbleTone[msg.role]}`}
                  >
                    {msg.content || (msg.role === "assistant" ? "..." : "")}
                  </motion.div>
                ))}
              </AnimatePresence>
              {loading && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass-bubble mr-auto flex max-w-[78%] items-center gap-2 rounded-[1.4rem] border-aqua/70 bg-aqua/28 px-4 py-2 text-sm font-semibold text-cyan-900">
                  <span>Maid is thinking</span>
                  <span className="sparkle-drift">❤</span>
                  <span className="sparkle-drift" style={{ animationDelay: "0.2s" }}>✦</span>
                  <span className="sparkle-drift" style={{ animationDelay: "0.4s" }}>❀</span>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

        {(error || uploadNotice || docsQuery.isLoading) && (
          <div className="shrink-0 rounded-xl border border-white/60 bg-white/50 px-3 py-2 text-sm font-medium text-slate-700 backdrop-blur-sm">
            {error && <p className="text-rose-700">{error}</p>}
            {!error && uploadNotice && <p>{uploadNotice}</p>}
            {!error && !uploadNotice && docsQuery.isLoading && <p>Loading study documents…</p>}
          </div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); void send(); }}
          className="shrink-0 rounded-2xl border border-white/70 bg-white/55 p-2 shadow-glowPink backdrop-blur-sm sm:p-2.5"
        >
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden" onChange={handleFileSelection} />
          <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="group grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/85 bg-gradient-to-br from-aqua/90 to-sky/85 text-slate-700 shadow-glowAqua transition hover:scale-105 focus:outline-none focus:ring-2 focus:ring-aqua/80"
            aria-label="上传课程材料（PDF、TXT、DOCX、MD）"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5 transition group-hover:rotate-12" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M8.5 12.5L14.7 6.3a3.1 3.1 0 114.4 4.4l-7.9 7.9a5.3 5.3 0 11-7.5-7.5l7.9-7.9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => setShowCourseFetch(true)}
            className="group grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/85 bg-gradient-to-br from-violet-400 to-purple-600 text-white shadow-md transition hover:scale-105 focus:outline-none focus:ring-2 focus:ring-violet-500"
            aria-label="Fetch course from NTU Learn"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <input
            value={input}
            onChange={(e) => { setInput(e.target.value); if (uploadNotice) setUploadNotice(null); }}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void send(); } }}
            placeholder="Ask your maid tutor anything…"
            className="h-11 flex-1 rounded-full border border-white/80 bg-white/50 px-4 text-sm font-semibold text-slate-800 placeholder:text-slate-600 shadow-inner focus:outline-none focus:ring-2 focus:ring-sakura/80"
            aria-label="Message"
          />
          <div className="relative">
            {sparkleBursts.map((burstId) => (
              <div key={burstId} className="pointer-events-none absolute inset-0">
                {Array.from({ length: 6 }, (_, i) => {
                  const angle = (i / 6) * Math.PI * 2;
                  return (
                    <motion.span
                      key={`${burstId}-${i}`}
                      className="absolute left-1/2 top-1/2 text-[11px] text-bubblegum"
                      initial={{ x: 0, y: 0, opacity: 0.2, scale: 0.5 }}
                      animate={{ x: Math.cos(angle) * 28, y: Math.sin(angle) * 20, opacity: [0.9, 0], scale: [0.8, 1.2] }}
                      transition={{ duration: 0.7, ease: "easeOut" }}
                    >
                      ✦
                    </motion.span>
                  );
                })}
              </div>
            ))}
            <button
              type="submit"
              disabled={loading}
              className="group grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/85 bg-gradient-to-br from-sakura/90 to-bubblegum/88 text-rose-900 shadow-glowPink transition hover:scale-105 disabled:cursor-not-allowed disabled:opacity-60"
              aria-label="Send message"
            >
              {loading ? <span className="text-xs font-extrabold">...</span> : (
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                  <path d="M12 21c-4.5-2.8-8-5.9-8-10a4.7 4.7 0 018.2-3.1A4.7 4.7 0 0120.4 11c0 4.1-3.5 7.2-8.4 10z" />
                </svg>
              )}
            </button>
          </div>
          </div>
          <p className="mt-1.5 text-center text-xs font-medium text-slate-600">
            {uploadMutation.isPending || fetchCourseMutation.isPending || organizeMutation.isPending ? "处理中…" : "按 Enter 发送"}
          </p>
        </form>

        {showCourseFetch && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" role="dialog" aria-modal="true" aria-labelledby="course-fetch-title">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-white/60 bg-white/95 shadow-xl backdrop-blur-sm"
            >
              <div className="shrink-0 border-b border-slate-200/80 p-4">
                <h2 id="course-fetch-title" className="mb-2 text-lg font-bold text-slate-800">Fetch course materials</h2>
                <p className="mb-3 text-sm text-slate-600">
                  <strong>Login-required (e.g. ntulearn):</strong> 1) Close Chrome, then start it with remote debugging. To use your existing profile (e.g. maythegod1772@gmail.com, already logged in): <code className="rounded bg-slate-200 px-1 text-xs">&quot;/Applications/Google Chrome.app/Contents/MacOS/Google Chrome&quot; --remote-debugging-port=9222 --user-data-dir=&quot;$HOME/Library/Application Support/Google/Chrome&quot; --profile-directory=&quot;Default&quot;</code> (for another profile see chrome://version). 2) Click <strong>Record</strong>, go to the course page in that Chrome window, then press <kbd className="rounded border bg-slate-100 px-1">Ctrl+Shift+D</kbd> to save. 3) Click <strong>Get</strong> to download via Playwright. — Or use the frame/paste + Qwen flow below (no login in iframe).
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    id="course-url"
                    type="url"
                    value={courseUrl}
                    onChange={(e) => setCourseUrl(e.target.value)}
                    placeholder="https://ntulearn.ntu.edu.sg/..."
                    className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
                  />
                  <button
                    type="button"
                    disabled={fetchCourseMutation.isPending}
                    onClick={() => {
                      const u = courseUrl.trim();
                      if (u) fetchCourseMutation.mutate({ url: u, mode: "record" });
                    }}
                    className="shrink-0 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-60"
                    title="Record steps in Chrome (must be running with --remote-debugging-port=9222)"
                  >
                    {fetchCourseMutation.isPending ? "…" : "Record (Playwright)"}
                  </button>
                  <button
                    type="button"
                    disabled={fetchCourseMutation.isPending || !courseUrl.trim()}
                    onClick={() => {
                      const pasted = pastedUrlForGet.trim();
                      const u = pasted || (() => {
                        const iframe = schoolIframeRef.current;
                        if (!iframe?.contentWindow) return courseUrl.trim();
                        try {
                          const params = new URLSearchParams(iframe.contentWindow.location.search);
                          return params.get("url") || courseUrl.trim();
                        } catch {
                          return courseUrl.trim();
                        }
                      })();
                      if (u) {
                        fetchCourseMutation.reset();
                        fetchCourseMutation.mutate({ url: u });
                      }
                    }}
                    className="shrink-0 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60"
                  >
                    {fetchCourseMutation.isPending ? "…" : "Get (Playwright or Qwen)"}
                  </button>
                </div>
                <div className="mt-3">
                  <label htmlFor="pasted-url-for-get" className="mb-1 block text-xs font-medium text-slate-600">
                    Or paste course page URL for Get (if frame failed or you opened it in a new tab)
                  </label>
                  <input
                    id="pasted-url-for-get"
                    type="url"
                    value={pastedUrlForGet}
                    onChange={(e) => setPastedUrlForGet(e.target.value)}
                    placeholder="Paste URL from address bar, then click Get"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
                  />
                </div>
              </div>
              <div className="relative min-h-0 flex-1 overflow-hidden p-4 pt-0">
                {iframeSrc ? (
                  <iframe
                    ref={schoolIframeRef}
                    src={iframeSrc}
                    title="School / course page"
                    className="h-[50vh] w-full rounded-lg border border-slate-300 bg-white"
                    sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                  />
                ) : (
                  <div className="flex h-[50vh] w-full items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50/80 text-slate-500">
                    Paste course page URL above and click Get, or use Record (Playwright).
                  </div>
                )}
              </div>
              {fetchCourseMutation.isPending && (
                <div className="shrink-0 flex items-center gap-3 border-t border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-800">
                  <svg className="h-5 w-5 animate-spin text-violet-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Fetching course content with Qwen…</span>
                </div>
              )}
              {fetchCourseMutation.isError && (
                <div className="shrink-0 rounded-b-2xl border-t border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                  {fetchCourseMutation.error instanceof Error
                    ? fetchCourseMutation.error.message
                    : "Course fetch failed."}
                </div>
              )}
              <div className="shrink-0 flex justify-end gap-2 border-t border-slate-200/80 p-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowCourseFetch(false);
                    setIframeSrc(null);
                    setPastedUrlForGet("");
                    fetchCourseMutation.reset();
                  }}
                  className="rounded-lg border border-slate-300 bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {showOrganize && organizeResult !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" role="dialog" aria-modal="true" aria-labelledby="organize-title">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl border border-white/60 bg-white/95 shadow-xl backdrop-blur-sm"
            >
              <div className="shrink-0 border-b border-slate-200/80 px-4 py-3">
                <h2 id="organize-title" className="text-lg font-bold text-slate-800">课程材料整理建议</h2>
                <p className="mt-1 text-sm text-slate-600">根据你上传的材料生成的学习顺序与重点～</p>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
                <div className="whitespace-pre-wrap rounded-xl border border-slate-200/80 bg-slate-50/60 px-4 py-3 text-sm leading-relaxed text-slate-800">
                  {organizeResult}
                </div>
              </div>
              <div className="shrink-0 flex justify-end gap-2 border-t border-slate-200/80 p-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowOrganize(false);
                    setOrganizeResult(null);
                  }}
                  className="rounded-lg border border-slate-300 bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                >
                  关闭
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </section>
  );
};
