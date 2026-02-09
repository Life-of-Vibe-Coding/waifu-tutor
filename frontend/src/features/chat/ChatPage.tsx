import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

import { chat, listDocuments, streamChat, uploadDocument } from "../../api/endpoints";
import { speakText } from "../../lib/tts";
import { useAppStore } from "../../state/appStore";
import type { CharacterMood, ChatMessage, CompanionStatus } from "../../types/domain";

const moodLabel: Record<CharacterMood, string> = {
  neutral: "Calm Focus",
  happy: "Sparkly Happy",
  encouraging: "Cheering You On",
  sad: "Soft Comfort",
  excited: "High Energy",
};

const statusLabel: Record<CompanionStatus, string> = {
  idle: "Idle",
  listening: "Listening",
  thinking: "Thinking",
  celebrating: "Yay!",
  comforting: "Comforting",
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

  const activeDocId = useAppStore((state) => state.activeDocId);
  const setActiveDocId = useAppStore((state) => state.setActiveDocId);
  const mood = useAppStore((state) => state.mood);
  const ttsEnabled = useAppStore((state) => state.ttsEnabled);
  const toggleTts = useAppStore((state) => state.toggleTts);
  const messages = useAppStore((state) => state.messages);
  const setMessages = useAppStore((state) => state.setMessages);
  const setMood = useAppStore((state) => state.setMood);
  const isListening = useAppStore((state) => state.isListening);
  const setListening = useAppStore((state) => state.setListening);
  const companionStatus = useAppStore((state) => state.companionStatus);
  const setCompanionStatus = useAppStore((state) => state.setCompanionStatus);
  const bumpAffection = useAppStore((state) => state.bumpAffection);
  const incrementSessionStreak = useAppStore((state) => state.incrementSessionStreak);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const celebrationTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const sparkleIdRef = useRef(0);
  const sparkleTimersRef = useRef<Array<ReturnType<typeof window.setTimeout>>>([]);

  const docsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  const readyDocs = useMemo(
    () => docsQuery.data?.filter((doc) => doc.status === "ready") ?? [],
    [docsQuery.data],
  );

  const triggerCelebration = () => {
    if (celebrationTimeoutRef.current) {
      window.clearTimeout(celebrationTimeoutRef.current);
    }
    setCompanionStatus("celebrating");
    celebrationTimeoutRef.current = window.setTimeout(() => {
      setCompanionStatus("idle");
    }, 1200);
  };

  const triggerSparkleTrail = () => {
    const id = sparkleIdRef.current + 1;
    sparkleIdRef.current = id;
    setSparkleBursts((previous) => [...previous, id]);

    const timer = window.setTimeout(() => {
      setSparkleBursts((previous) => previous.filter((value) => value !== id));
      sparkleTimersRef.current = sparkleTimersRef.current.filter((candidate) => candidate !== timer);
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
      setUploadNotice(`Uploaded ${doc.title} and selected it as context.`);
      triggerCelebration();
    },
    onError: () => {
      setMood("sad");
      setCompanionStatus("comforting");
      setUploadNotice("Upload failed. Please try another document.");
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const typing = input.trim().length > 0;
    setListening(loading || typing);

    if (loading && companionStatus !== "celebrating") {
      setCompanionStatus("thinking");
      return;
    }

    if (typing && companionStatus !== "celebrating") {
      setCompanionStatus("listening");
      return;
    }

    if (!typing && !loading && companionStatus === "listening") {
      setCompanionStatus("idle");
    }
  }, [input, loading, companionStatus, setCompanionStatus, setListening]);

  useEffect(
    () => () => {
      setListening(false);
      if (celebrationTimeoutRef.current) {
        window.clearTimeout(celebrationTimeoutRef.current);
      }
      sparkleTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      sparkleTimersRef.current = [];
    },
    [setListening],
  );

  const send = async () => {
    if (!input.trim() || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    setCompanionStatus("thinking");
    bumpAffection(2);
    incrementSessionStreak();
    triggerSparkleTrail();

    const userMessage = { role: "user" as const, content: input.trim() };
    const history = [...messages, userMessage];
    setMessages([...history, { role: "assistant", content: "" }]);
    setInput("");

    let assistantText = "";

    try {
      await streamChat(userMessage.content, history, activeDocId, (event) => {
        if (event.type === "token") {
          assistantText = `${assistantText} ${String(event.payload.token)}`.trim();
          setMessages([...history, { role: "assistant", content: assistantText }]);
        }

        if (event.type === "mood" && event.payload?.mood) {
          setMood(event.payload.mood as CharacterMood);
        }

        if (event.type === "done") {
          const finalMessage = String(event.payload.message ?? assistantText);
          setMessages([...history, { role: "assistant", content: finalMessage }]);
          if (ttsEnabled) {
            speakText(finalMessage);
          }
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
        if (ttsEnabled) {
          speakText(response.message.content);
        }
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

  const handleFileSelection = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) {
      return;
    }

    const isVideo = file.type.startsWith("video/") || /\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(file.name);
    if (isVideo) {
      setUploadNotice("Video upload is not supported yet. Please upload PDF, DOCX, TXT, or MD.");
      setCompanionStatus("comforting");
      return;
    }

    const isSupportedDoc = /\.(pdf|docx|txt|md)$/i.test(file.name);
    if (!isSupportedDoc) {
      setUploadNotice("Unsupported file type. Please upload PDF, DOCX, TXT, or MD.");
      setCompanionStatus("comforting");
      return;
    }

    setUploadNotice(null);
    uploadMutation.mutate(file);
  };

  return (
    <section className="relative h-full w-full">
      <div className="pointer-events-none mx-auto flex h-full w-full max-w-6xl flex-col px-3 pb-36 pt-4 lg:pr-72 sm:px-6 sm:pt-6">
        <div className="pointer-events-auto flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-white/65 bg-white/32 px-4 py-3 shadow-glowAqua">
          <div>
            <p className="font-display text-2xl font-bold text-ink">Waifu Tutor</p>
            <p className="text-xs font-extrabold uppercase tracking-[0.15em] text-slate-700">
              Mood · {moodLabel[mood]} · {statusLabel[companionStatus]}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="rounded-full border border-white/80 bg-white/52 px-2 py-1 text-[11px] font-extrabold uppercase tracking-[0.12em] text-slate-700">
              Context
            </label>
            <select
              value={activeDocId ?? ""}
              onChange={(event) => setActiveDocId(event.target.value || null)}
              className="rounded-full border border-white/80 bg-white/62 px-3 py-2 text-sm font-semibold text-slate-800 shadow-soft focus:outline-none focus:ring-2 focus:ring-sakura"
            >
              <option value="">No document selected</option>
              {readyDocs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.title}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={toggleTts}
              className={`rounded-full border px-4 py-2 text-sm font-extrabold transition ${
                ttsEnabled
                  ? "border-aqua/90 bg-aqua/65 text-cyan-900"
                  : "border-white/80 bg-white/42 text-slate-700"
              }`}
            >
              Voice {ttsEnabled ? "On" : "Off"}
            </button>
          </div>
        </div>

        <div className="mt-4 flex-1 overflow-hidden rounded-[2rem] border border-white/65 bg-white/20 p-2 shadow-[0_34px_90px_rgba(66,76,128,0.34)] sm:p-3">
          <div className="h-full rounded-[1.6rem] border border-white/60 bg-white/16 p-2 sm:p-3">
            <div className="h-full space-y-3 overflow-y-auto rounded-[1.2rem] border border-white/45 bg-white/12 px-3 py-4 sm:px-5">
              {messages.length === 0 && (
                <motion.p
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass-bubble rounded-2xl px-4 py-3 text-sm font-semibold text-slate-700"
                >
                  Ask a question to start. Your maid tutor is ready to help.
                </motion.p>
              )}

              <AnimatePresence initial={false}>
                {messages.map((message, index) => (
                  <motion.div
                    key={`${message.role}-${index}`}
                    initial={{ opacity: 0, y: 26, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8, scale: 0.92 }}
                    transition={{ type: "spring", stiffness: 250, damping: 22, mass: 0.7 }}
                    className={`glass-bubble max-w-[92%] rounded-[1.45rem] px-4 py-3 text-sm leading-relaxed ${bubbleTone[message.role]}`}
                  >
                    {message.content || (message.role === "assistant" ? "..." : "")}
                  </motion.div>
                ))}
              </AnimatePresence>

              {loading && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass-bubble mr-auto flex max-w-[78%] items-center gap-2 rounded-[1.4rem] border-aqua/70 bg-aqua/28 px-4 py-2 text-sm font-semibold text-cyan-900"
                >
                  <span>Maid is thinking</span>
                  <span className="sparkle-drift">❤</span>
                  <span className="sparkle-drift" style={{ animationDelay: "0.2s" }}>
                    ✦
                  </span>
                  <span className="sparkle-drift" style={{ animationDelay: "0.4s" }}>
                    ❀
                  </span>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>

        <div className="pointer-events-auto mt-3 rounded-xl border border-white/65 bg-white/46 px-3 py-2 text-xs font-semibold text-slate-700">
          {error && <p className="text-rose-700">{error}</p>}
          {!error && uploadNotice && <p>{uploadNotice}</p>}
          {!error && !uploadNotice && docsQuery.isLoading && <p>Loading study documents...</p>}
          {!error && !uploadNotice && !docsQuery.isLoading && !activeDocId && (
            <p>No document context selected. You can still chat without one.</p>
          )}
        </div>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
        className="pointer-events-auto absolute bottom-4 left-1/2 w-[calc(100%-1rem)] max-w-4xl -translate-x-1/2 rounded-[1.8rem] border border-white/72 bg-white/48 p-2 shadow-glowPink sm:bottom-6 sm:w-[calc(100%-2rem)] sm:p-3"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md,video/*"
          className="hidden"
          onChange={handleFileSelection}
        />

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="group grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/85 bg-gradient-to-br from-aqua/90 to-sky/85 text-slate-700 shadow-glowAqua transition hover:scale-105"
            aria-label="Upload a document or video"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5 transition group-hover:rotate-12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path
                d="M8.5 12.5L14.7 6.3a3.1 3.1 0 114.4 4.4l-7.9 7.9a5.3 5.3 0 11-7.5-7.5l7.9-7.9"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>

          <input
            value={input}
            onChange={(event) => {
              setInput(event.target.value);
              if (uploadNotice) {
                setUploadNotice(null);
              }
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void send();
              }
            }}
            placeholder="Ask your maid tutor anything..."
            className="h-11 flex-1 rounded-full border border-white/80 bg-white/45 px-4 text-sm font-semibold text-slate-800 placeholder:text-slate-500 shadow-inner focus:outline-none focus:ring-2 focus:ring-sakura"
          />

          <div className="relative">
            {sparkleBursts.map((burstId) => (
              <div key={burstId} className="pointer-events-none absolute inset-0">
                {Array.from({ length: 6 }, (_, index) => {
                  const angle = (index / 6) * Math.PI * 2;
                  return (
                    <motion.span
                      key={`${burstId}-${index}`}
                      className="absolute left-1/2 top-1/2 text-[11px] text-bubblegum"
                      initial={{ x: 0, y: 0, opacity: 0.2, scale: 0.5 }}
                      animate={{
                        x: Math.cos(angle) * 28,
                        y: Math.sin(angle) * 20,
                        opacity: [0.9, 0],
                        scale: [0.8, 1.2],
                      }}
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
              {loading ? (
                <span className="text-xs font-extrabold">...</span>
              ) : (
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                  <path d="M12 21c-4.5-2.8-8-5.9-8-10a4.7 4.7 0 018.2-3.1A4.7 4.7 0 0120.4 11c0 4.1-3.5 7.2-8.4 10z" />
                </svg>
              )}
            </button>
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between px-1 text-[11px] font-extrabold uppercase tracking-[0.09em] text-slate-700/90">
          <span>{loading ? "Maid is thinking" : isListening ? "Maid is listening" : "Ask your tutor anything"}</span>
          <span>{uploadMutation.isPending ? "Uploading document" : "Press Enter to send"}</span>
        </div>
      </form>
    </section>
  );
};
