import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import React, { type ChangeEvent, useEffect, useRef, useState } from "react";
import { getChatErrorMessage } from "@/lib/chat-error";
import { chat, streamChat, uploadDocument, confirmDocumentSubject } from "@/lib/endpoints";
import { speakText } from "@/lib/tts";
import { useAppStore } from "@/state/appStore";
import type { CharacterMood, ChatMessage, DocumentMeta } from "@/types/domain";

const moodLabel: Record<CharacterMood, string> = {
  neutral: "Calm Focus",
  happy: "Sparkly Happy",
  encouraging: "Cheering You On",
  sad: "Soft Comfort",
  excited: "High Energy",
  gentle: "Gentle",
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
  const [subjectConfirmPending, setSubjectConfirmPending] = useState<{
    docId: string;
    docTitle: string;
    suggestedSubjectId: string;
    suggestedSubjectName: string;
  } | null>(null);

  const activeDocId = useAppStore((s) => s.activeDocId);
  const sessionId = useAppStore((s) => s.sessionId);
  const setActiveDocId = useAppStore((s) => s.setActiveDocId);
  const setSessionId = useAppStore((s) => s.setSessionId);
  const clearConversation = useAppStore((s) => s.clearConversation);
  const mood = useAppStore((s) => s.mood);
  const ttsEnabled = useAppStore((s) => s.ttsEnabled);
  const toggleTts = useAppStore((s) => s.toggleTts);
  const messages = useAppStore((s) => s.messages);
  const setMessages = useAppStore((s) => s.setMessages);
  const setMood = useAppStore((s) => s.setMood);
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
      await streamChat(userMessage.content, history, activeDocId, sessionId, (event) => {
        if (event.type === "token") {
          const token = (event.payload as { token?: string })?.token;
          assistantText = `${assistantText} ${String(token ?? "")}`.trim();
          setMessages([...history, { role: "assistant", content: assistantText }]);
        }
        if (event.type === "mood" && (event.payload as { mood?: string })?.mood) {
          setMood((event.payload as { mood: CharacterMood }).mood);
        }
        if (event.type === "done") {
          const donePayload = event.payload as { message?: string; session_id?: string };
          const finalMessage = String(donePayload?.message ?? assistantText);
          setMessages([...history, { role: "assistant", content: finalMessage }]);
          if (donePayload?.session_id) setSessionId(donePayload.session_id);
          if (ttsEnabled) speakText(finalMessage);
          bumpAffection(3);
          setMood("encouraging");
          triggerCelebration();
        }
      });
    } catch (streamErr) {
      try {
        const response = await chat(userMessage.content, history, activeDocId, sessionId);
        setMessages([...history, response.message]);
        if (response.session_id) setSessionId(response.session_id);
        setMood(response.mood);
        if (ttsEnabled) speakText(response.message.content);
        bumpAffection(3);
        triggerCelebration();
      } catch (chatErr) {
        setMessages(history);
        const msg = getChatErrorMessage(streamErr, chatErr);
        setError(msg);
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
      {/* Header */}
      <header className="flex shrink-0 items-center justify-between border-b border-white/20 bg-white/10 px-6 py-4 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-xl font-bold tracking-tight text-slate-800 sm:text-2xl">Waifu Tutor</h1>
            <span className="rounded-full border border-white/40 bg-white/20 px-3 py-1 text-xs font-semibold text-slate-700 backdrop-blur-sm" title="Companion mood">
              {moodLabel[mood]}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                clearConversation();
                setMood("neutral");
                setError(null);
                setUploadNotice(null);
              }}
              className="rounded-full border border-white/30 bg-white/10 px-4 py-1.5 text-sm font-bold text-slate-700 transition-all hover:bg-white/20"
            >
              New Chat
            </button>
            <button
              type="button"
              onClick={toggleTts}
              aria-pressed={ttsEnabled}
              className={`rounded-full border px-4 py-1.5 text-sm font-bold transition-all ${
                ttsEnabled 
                  ? "border-aqua/50 bg-aqua/20 text-cyan-900 shadow-[0_0_10px_rgba(157,231,255,0.3)]" 
                  : "border-white/30 bg-white/10 text-slate-600 hover:bg-white/20"
              }`}
            >
              Voice {ttsEnabled ? "On" : "Off"}
            </button>
          </div>
      </header>

      {/* Confirmation Banner */}
      {subjectConfirmPending && (
        <div className="mx-4 mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sakura/40 bg-sakura/10 px-5 py-3 backdrop-blur-sm">
          <span className="text-sm font-medium text-slate-800">
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
              className="rounded-full bg-green-500 px-4 py-1.5 text-sm font-bold text-white shadow-lg shadow-green-500/20 transition hover:bg-green-600 hover:shadow-green-500/30 disabled:opacity-50"
            >
              {confirmSubjectMutation.isPending ? "…" : "Yes"}
            </button>
            <button
              type="button"
              disabled={confirmSubjectMutation.isPending}
              onClick={() => { setSubjectConfirmPending(null); setUploadNotice(null); }}
              className="rounded-full bg-white/40 px-4 py-1.5 text-sm font-semibold text-slate-700 hover:bg-white/60"
            >
              No
            </button>
          </div>
        </div>
      )}

      {/* Chat Area */}
      <div className="flex min-h-0 flex-1 flex-col gap-4 p-4 sm:p-6">
        {/* Messages List */}
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div
            ref={messagesScrollContainerRef}
            className="flex min-h-0 flex-1 flex-col space-y-4 overflow-y-auto pr-2 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/30 hover:scrollbar-thumb-white/50"
          >
              {messages.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mx-auto mt-8 max-w-sm rounded-3xl border border-white/30 bg-white/20 p-6 text-center text-slate-600 backdrop-blur-sm"
                >
                  <p className="font-medium">Ask a question to start.</p>
                  <p className="mt-1 text-sm opacity-80">Your maid tutor is ready to help.</p>
                </motion.div>
              )}
              
              <AnimatePresence initial={false}>
                {messages.map((msg, i) => (
                  <motion.div
                    key={`${msg.role}-${i}`}
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ type: "spring", stiffness: 300, damping: 25 }}
                    className={`relative max-w-[85%] rounded-[1.5rem] px-5 py-3.5 text-sm leading-relaxed shadow-sm backdrop-blur-sm ${bubbleTone[msg.role]}`}
                  >
                    {msg.content || (msg.role === "assistant" ? "..." : "")}
                  </motion.div>
                ))}
              </AnimatePresence>
              
              {loading && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }} 
                  animate={{ opacity: 1, y: 0 }} 
                  className="mr-auto flex items-center gap-2 rounded-full border border-aqua/30 bg-aqua/10 px-4 py-2 text-sm font-medium text-cyan-900 backdrop-blur-sm"
                >
                  <span>Maid is thinking</span>
                  <div className="flex gap-0.5">
                    <span className="animate-bounce delay-0">.</span>
                    <span className="animate-bounce delay-100">.</span>
                    <span className="animate-bounce delay-200">.</span>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

        {/* Error / Notice */}
        {(error || uploadNotice) && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-rose-200 bg-rose-50/80 px-4 py-3 text-sm text-rose-800 backdrop-blur-sm"
          >
            {error && <p className="font-semibold">{error}</p>}
            {!error && uploadNotice && <p>{uploadNotice}</p>}
          </motion.div>
        )}

        {/* Input Area */}
        <form
          onSubmit={(e) => { e.preventDefault(); void send(); }}
          className="relative shrink-0 rounded-[2rem] border border-white/60 bg-white/40 p-2 shadow-lg shadow-indigo-500/5 backdrop-blur-md transition-all focus-within:bg-white/60 focus-within:shadow-indigo-500/10"
        >
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden" onChange={handleFileSelection} />
          
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="group flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/50 text-slate-600 transition hover:bg-white/80 hover:text-indigo-600"
              title="Upload study materials"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5 transition-transform group-hover:rotate-12" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 4v16m-8-8h16" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            
            <input
              value={input}
              onChange={(e) => { setInput(e.target.value); if (uploadNotice) setUploadNotice(null); }}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void send(); } }}
              placeholder="Ask your maid tutor anything..."
              className="h-10 flex-1 bg-transparent px-2 text-sm font-medium text-slate-800 placeholder:text-slate-500 focus:outline-none"
            />
            
            <div className="relative">
              {sparkleBursts.map((burstId) => (
                <div key={burstId} className="pointer-events-none absolute inset-0">
                  {/* Sparkle effects handled by CSS/Framer elsewhere, simplified here for layout */}
                </div>
              ))}
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md transition hover:scale-105 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14m-7-7l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          </div>
        </form>
      </div>
    </section>
  );
};
