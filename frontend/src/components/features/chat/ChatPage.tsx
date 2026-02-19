import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { type ChangeEvent, useEffect, useRef, useState } from "react";
import { getChatErrorMessage, getChatErrorKind } from "@/lib/chat-error";
import {
  ackReminder,
  chat,
  listDueReminders,
  streamChat,
  submitHitlResponse,
  uploadDocument,
  getInitialGreeting,
  type StreamDonePayload,
  type StreamHitlCheckpointPayload,
  type StreamMoodPayload,
  type StreamTokenPayload,
} from "@/lib/endpoints";
import type { ReminderPayload } from "@/lib/endpoints";
import { AssistantMessageQueue, type AssistantQueueAction } from "@/lib/assistantMessageQueue";
import { speakText } from "@/lib/tts";
import { useAppStore } from "@/state/appStore";
import type { CharacterMood, ChatMessage } from "@/types/domain";

const moodLabel: Record<CharacterMood, string> = {
  neutral: "Calm Focus",
  happy: "Sparkly Happy",
  encouraging: "Cheering You On",
  sad: "Soft Comfort",
  excited: "High Energy",
  gentle: "Gentle",
};

/** ~330 WPM - 1.5x faster than ~220 WPM */
const MS_PER_WORD = 180;

/** How long the speech bubble stays visible after chat/repeat completes */
const BUBBLE_HIDE_DELAY_MS = 6000;
const QUEUE_COOLDOWN_MS = 3000;
const QUEUE_TICK_MS = 120;

function WordByWordText({ content, resetKey }: { content: string; resetKey: number }) {
  const words = content.trim() ? content.trim().split(/\s+/) : [];
  const [visibleCount, setVisibleCount] = useState(0);
  const prevKeyRef = useRef(resetKey);

  useEffect(() => {
    if (prevKeyRef.current !== resetKey) {
      prevKeyRef.current = resetKey;
      setVisibleCount(0);
    }
  }, [resetKey]);

  useEffect(() => {
    if (visibleCount >= words.length) return;
    const id = setTimeout(() => setVisibleCount((c) => Math.min(c + 1, words.length)), MS_PER_WORD);
    return () => clearTimeout(id);
  }, [visibleCount, words.length]);

  const visible = words.slice(0, visibleCount).join(" ");
  return <>{visible || (words.length ? "" : "...")}</>;
}

export const ChatPage = () => {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);
  const [sparkleBursts, setSparkleBursts] = useState<number[]>([]);
  const [reminderToast, setReminderToast] = useState<{
    message: string;
    reminderId?: string;
  } | null>(null);
  const [isBubbleVisible, setIsBubbleVisible] = useState(false);
  const [responseId, setResponseId] = useState(0);
  const [pendingHitl, setPendingHitl] = useState<StreamHitlCheckpointPayload | null>(null);
  const [hitlSubmitting, setHitlSubmitting] = useState(false);

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
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const messagesScrollContainerRef = useRef<HTMLDivElement | null>(null);
  const lastScrolledMessageCountRef = useRef(0);
  const celebrationTimeoutRef = useRef<number | ReturnType<typeof setTimeout> | null>(null);
  const sparkleIdRef = useRef(0);
  const sparkleTimersRef = useRef<Array<number | ReturnType<typeof setTimeout>>>([]);
  const initialGreetingFetchedRef = useRef(false);
  const userHasSentMessageRef = useRef(false);
  const reminderTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const bubbleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queueRef = useRef(new AssistantMessageQueue({ cooldownMs: QUEUE_COOLDOWN_MS }));
  const queueMessageIndexByStreamRef = useRef<Map<string, number>>(new Map());
  const localQueueIdRef = useRef(0);
  const ttsEnabledRef = useRef(ttsEnabled);
  const applyQueueActionsRef = useRef<(actions: AssistantQueueAction[]) => void>(() => {});

  ttsEnabledRef.current = ttsEnabled;

  useEffect(() => {
    if (messages.length !== 0 || initialGreetingFetchedRef.current) return;
    initialGreetingFetchedRef.current = true;
    getInitialGreeting(sessionId)
      .then(({ message, session_id }) => {
        if (message && session_id && !userHasSentMessageRef.current) {
          setMessages([{ role: "assistant", content: message }]);
          setSessionId(session_id);
          setMood("happy");
        }
      })
      .catch(() => {});
  }, [messages.length, sessionId, setMessages, setSessionId, setMood]);

  // Poll for due break reminders on mount / session change (e.g. after refresh)
  useEffect(() => {
    return () => {
      if (reminderTimerRef.current) clearTimeout(reminderTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    listDueReminders(sessionId).then((list) => {
      const first = list[0];
      if (first) {
        setReminderToast({ message: first.message || "Time's up! Ready to get back?", reminderId: first.id });
        first.id && ackReminder(first.id).catch(() => {});
      }
      for (let i = 1; i < list.length; i++) {
        list[i].id && ackReminder(list[i].id).catch(() => {});
      }
    }).catch(() => {});
  }, [sessionId]);

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

  const nextLocalQueueId = (prefix: string) => {
    localQueueIdRef.current += 1;
    return `${prefix}-${Date.now()}-${localQueueIdRef.current}`;
  };

  const scheduleReminderToast = (br?: ReminderPayload) => {
    if (!br?.due_at) return;
    if (reminderTimerRef.current) clearTimeout(reminderTimerRef.current);
    const dueAt = new Date(br.due_at).getTime();
    const ms = Math.max(0, dueAt - Date.now());
    reminderTimerRef.current = setTimeout(() => {
      reminderTimerRef.current = null;
      setReminderToast({
        message: br.kind === "focus" ? "Focus time's up! Consider a short break." : "Break's over — ready to get back?",
        reminderId: br.reminder_id,
      });
      if (br.reminder_id) ackReminder(br.reminder_id).catch(() => {});
    }, ms);
  };

  const applyQueueActions = (actions: AssistantQueueAction[]) => {
    for (const action of actions) {
      if (action.type === "started") {
        if (bubbleTimerRef.current) clearTimeout(bubbleTimerRef.current);
        setIsBubbleVisible(true);
        setResponseId((r) => r + 1);

        const state = useAppStore.getState();
        const assistantMessage: ChatMessage = { role: "assistant", content: action.entry.text };
        const nextMessages: ChatMessage[] = [...state.messages, assistantMessage];
        useAppStore.setState({ messages: nextMessages });
        queueMessageIndexByStreamRef.current.set(action.entry.streamId, nextMessages.length - 1);
        continue;
      }

      if (action.type === "updated") {
        if (bubbleTimerRef.current) clearTimeout(bubbleTimerRef.current);
        setIsBubbleVisible(true);

        const index = queueMessageIndexByStreamRef.current.get(action.entry.streamId);
        const state = useAppStore.getState();
        const nextMessages: ChatMessage[] = [...state.messages];
        if (
          index === undefined
          || index < 0
          || index >= nextMessages.length
          || nextMessages[index]?.role !== "assistant"
        ) {
          const assistantMessage: ChatMessage = { role: "assistant", content: action.entry.text };
          nextMessages.push(assistantMessage);
          queueMessageIndexByStreamRef.current.set(action.entry.streamId, nextMessages.length - 1);
        } else {
          nextMessages[index] = { role: "assistant", content: action.entry.text };
        }
        useAppStore.setState({ messages: nextMessages });
        continue;
      }

      if (action.type === "completed") {
        queueMessageIndexByStreamRef.current.delete(action.entry.streamId);
        const meta = action.entry.meta;
        if (meta.sessionId) setSessionId(meta.sessionId);
        if (meta.mood) setMood(meta.mood);
        else if (action.entry.source === "sse") setMood("encouraging");
        if (meta.reminder) scheduleReminderToast(meta.reminder);
        if (ttsEnabledRef.current && action.entry.text.trim()) speakText(action.entry.text);

        if (action.entry.source === "sse") {
          bumpAffection(3);
          triggerCelebration();
        }

        if (bubbleTimerRef.current) clearTimeout(bubbleTimerRef.current);
        bubbleTimerRef.current = setTimeout(() => {
          setIsBubbleVisible(false);
        }, BUBBLE_HIDE_DELAY_MS);
      }
    }
  };
  applyQueueActionsRef.current = applyQueueActions;

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
    const timer = window.setInterval(() => {
      const actions = queueRef.current.tick();
      if (actions.length > 0) applyQueueActionsRef.current(actions);
    }, QUEUE_TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

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
    queueRef.current.clear();
    queueMessageIndexByStreamRef.current.clear();
  }, [setListening]);

  const repeatLastMessage = () => {
    const lastAssistantMsg = [...messages].reverse().find(m => m.role === "assistant");
    if (!lastAssistantMsg) return;
    
    setResponseId((r) => r + 1);
    setIsBubbleVisible(true);
    if (bubbleTimerRef.current) clearTimeout(bubbleTimerRef.current);
    
    if (ttsEnabled) speakText(lastAssistantMsg.content);
    
    bubbleTimerRef.current = setTimeout(() => {
      setIsBubbleVisible(false);
    }, BUBBLE_HIDE_DELAY_MS);
  };

  /** Persona line shown when user uploads files (no generic "Uploaded N files" banner). */
  const UPLOAD_ACK_MESSAGE =
    "Well received! Let me process these files for you.";

  const send = async (
    overrideContent?: string,
    docIdOverride?: string | null,
    options?: { historyAlreadySet?: ChatMessage[] }
  ) => {
    const content = overrideContent ?? input;
    if (!content.trim() || loading) return;
    userHasSentMessageRef.current = true;
    setLoading(true);
    setError(null);
    setValidationError(null);
    setCompanionStatus("thinking");
    setIsBubbleVisible(false);
    if (bubbleTimerRef.current) clearTimeout(bubbleTimerRef.current);
    
    bumpAffection(2);
    incrementSessionStreak();
    triggerSparkleTrail();
    const userMessage: ChatMessage = { role: "user", content: content.trim() };
    const currentMessages = useAppStore.getState().messages;
    const history = options?.historyAlreadySet ?? [...currentMessages, userMessage];
    if (!options?.historyAlreadySet) setMessages(history);
    if (!overrideContent) setInput("");
    const docId = docIdOverride !== undefined ? docIdOverride : activeDocId;
    const fallbackStreamId = nextLocalQueueId("unknown-stream");
    const touchedStreamIds = new Set<string>();
    let warnedMissingStreamId = false;

    const resolveStreamId = (maybeStreamId?: string) => {
      const streamId = String(maybeStreamId ?? "").trim();
      if (streamId) return streamId;
      if (!warnedMissingStreamId) {
        console.warn("SSE stream event missing stream_id; using fallback stream id.");
        warnedMissingStreamId = true;
      }
      return fallbackStreamId;
    };

    try {
      await streamChat(userMessage.content, history, docId, sessionId, (event) => {
        if (event.type === "token") {
          const payload = event.payload as StreamTokenPayload;
          const streamId = resolveStreamId(payload.stream_id);
          touchedStreamIds.add(streamId);
          const actions = queueRef.current.enqueueChunk(streamId, String(payload.token ?? ""), "sse");
          if (actions.length > 0) applyQueueActions(actions);
        }
        if (event.type === "mood") {
          const payload = event.payload as StreamMoodPayload;
          if (!payload.mood) return;
          const streamId = resolveStreamId(payload.stream_id);
          touchedStreamIds.add(streamId);
          const actions = queueRef.current.upsertMeta(streamId, { mood: payload.mood as CharacterMood }, "sse");
          if (actions.length > 0) applyQueueActions(actions);
        }
        if (event.type === "reminder") {
          const br = event.payload as ReminderPayload;
          const streamId = resolveStreamId(br.stream_id);
          touchedStreamIds.add(streamId);
          const actions = queueRef.current.upsertMeta(streamId, { reminder: br }, "sse");
          if (actions.length > 0) applyQueueActions(actions);
        }
        if (event.type === "hitl_checkpoint") {
          const payload = event.payload as StreamHitlCheckpointPayload;
          const streamId = resolveStreamId(payload.stream_id);
          touchedStreamIds.add(streamId);
          const actions = queueRef.current.markDone(streamId, undefined, {
            sessionId: payload.session_id ?? null,
          });
          if (actions.length > 0) applyQueueActions(actions);
          setPendingHitl(payload);
          if (payload.session_id) setSessionId(payload.session_id);
        }
        if (event.type === "done") {
          const donePayload = event.payload as StreamDonePayload;
          const streamId = resolveStreamId(donePayload.stream_id);
          touchedStreamIds.add(streamId);
          const actions = queueRef.current.markDone(
            streamId,
            donePayload.message,
            {
              sessionId: donePayload.session_id ?? null,
              reminder: donePayload.reminder,
            }
          );
          if (actions.length > 0) applyQueueActions(actions);
        }
      });
    } catch (streamErr) {
      for (const streamId of touchedStreamIds) {
        const actions = queueRef.current.markDone(streamId);
        if (actions.length > 0) applyQueueActions(actions);
      }
      try {
        const response = await chat(userMessage.content, history, docId, sessionId);
        if (response.hitl) {
          setPendingHitl(response.hitl as StreamHitlCheckpointPayload);
          if (response.session_id) setSessionId(response.session_id);
          return;
        }
        const fallbackQueueStreamId = nextLocalQueueId("chat-fallback");
        const actions = queueRef.current.enqueueLocalMessage(
          fallbackQueueStreamId,
          response.message!.content,
          "sse",
          {
            sessionId: response.session_id ?? null,
            mood: response.mood,
            reminder: response.reminder,
          }
        );
        if (actions.length > 0) applyQueueActions(actions);
      } catch (chatErr) {
        setMessages(history);
        const msg = getChatErrorMessage(streamErr, chatErr);
        const kind = getChatErrorKind(streamErr, chatErr);
        if (kind === "validation") {
          setValidationError(msg);
          setError(null);
        } else {
          setError(msg);
          setValidationError(null);
          setMood("sad");
          setCompanionStatus("comforting");
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleHitlApprove = async () => {
    if (!pendingHitl || hitlSubmitting) return;
    setHitlSubmitting(true);
    try {
      const response = await submitHitlResponse(
        pendingHitl.session_id,
        pendingHitl.checkpoint_id,
        { approved: true },
      );
      setPendingHitl(null);
      if (response.hitl) {
        setPendingHitl(response.hitl as StreamHitlCheckpointPayload);
        if (response.session_id) setSessionId(response.session_id);
      } else if (response.message) {
        const fallbackStreamId = nextLocalQueueId("hitl-resume");
        const actions = queueRef.current.enqueueLocalMessage(
          fallbackStreamId,
          response.message.content,
          "sse",
          {
            sessionId: response.session_id ?? null,
            mood: response.mood,
            reminder: response.reminder,
          },
        );
        if (actions.length > 0) applyQueueActions(actions);
        if (response.mood) setMood(response.mood);
      }
    } catch (err) {
      setError((err as Error).message ?? "Failed to submit");
    } finally {
      setHitlSubmitting(false);
    }
  };

  const handleHitlCancel = async () => {
    if (!pendingHitl || hitlSubmitting) return;
    setHitlSubmitting(true);
    try {
      await submitHitlResponse(pendingHitl.session_id, pendingHitl.checkpoint_id, { cancelled: true });
      setPendingHitl(null);
    } catch (err) {
      setError((err as Error).message ?? "Failed to cancel");
    } finally {
      setHitlSubmitting(false);
    }
  };

  const handleHitlSelect = async (option: string) => {
    if (!pendingHitl || hitlSubmitting) return;
    setHitlSubmitting(true);
    try {
      const response = await submitHitlResponse(
        pendingHitl.session_id,
        pendingHitl.checkpoint_id,
        { selected: option },
      );
      setPendingHitl(null);
      if (response.hitl) {
        setPendingHitl(response.hitl as StreamHitlCheckpointPayload);
        if (response.session_id) setSessionId(response.session_id);
      } else if (response.message) {
        const fallbackStreamId = nextLocalQueueId("hitl-resume");
        const actions = queueRef.current.enqueueLocalMessage(
          fallbackStreamId,
          response.message.content,
          "sse",
          {
            sessionId: response.session_id ?? null,
            mood: response.mood,
            reminder: response.reminder,
          },
        );
        if (actions.length > 0) applyQueueActions(actions);
        if (response.mood) setMood(response.mood);
      }
    } catch (err) {
      setError((err as Error).message ?? "Failed to submit");
    } finally {
      setHitlSubmitting(false);
    }
  };

  const runUploadFlow = async (
    validFiles: File[],
    folderName: string | null,
  ) => {
    setUploadNotice(`Uploading ${validFiles.length} files...`);
    const uploadedNames: string[] = [];
    let lastErrorMsg = "";

    for (const file of validFiles) {
      try {
        const doc = await uploadDocument(file, folderName);
        uploadedNames.push(doc.filename);
      } catch (err: unknown) {
        const errObj = err as { response?: { data?: { detail?: string | { message?: string }; message?: string } }; message?: string };
        console.error("Upload failed for", file.name, err);
        const d = errObj.response?.data?.detail;
        lastErrorMsg = typeof d === "object" && d?.message
          ? d.message
          : (typeof d === "string" ? d : errObj.response?.data?.message ?? errObj.message ?? "Unknown error");
      }
    }

    if (uploadedNames.length > 0) {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      setUploadNotice(null);
      // Upload confirmation already includes uploaded filenames; avoid duplicate doc attachment.
      setActiveDocId(null);
      triggerCelebration();
      setMood("excited");
      bumpAffection(2);
      const msg = folderName
        ? `I've uploaded a folder '${folderName}' with files: ${uploadedNames.join(", ")}. Please reason about the folder and files, propose where they belong, and ask for my confirmation before organizing.`
        : `I've uploaded these files: ${uploadedNames.join(", ")}. Please reason about what they are, propose where they belong, and ask for my confirmation before organizing.`;
      const userMsg: ChatMessage = { role: "user", content: msg };
      const currentMsgs = useAppStore.getState().messages;
      const historyWithUser = [...currentMsgs, userMsg];
      setMessages(historyWithUser);
      const uploadAckStreamId = nextLocalQueueId("upload-ack");
      const ackActions = queueRef.current.enqueueLocalMessage(uploadAckStreamId, UPLOAD_ACK_MESSAGE, "local");
      if (ackActions.length > 0) applyQueueActions(ackActions);
      void send(msg, null, { historyAlreadySet: historyWithUser });
    } else {
      setUploadNotice(`Upload failed: ${lastErrorMsg}`);
      setMood("sad");
      setCompanionStatus("comforting");
    }
  };

  const handleFileSelection = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const fileList = Array.from(files);
    e.target.value = "";

    const validFiles = fileList.filter((f) =>
      /\.(pdf|docx|txt|md)$/i.test(f.name) &&
      !f.type.startsWith("video/") &&
      !/\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(f.name)
    );

    if (validFiles.length === 0) {
      setUploadNotice("Please upload course materials: PDF, TXT, DOCX, or MD.");
      setCompanionStatus("comforting");
      return;
    }

    await runUploadFlow(validFiles, null);
  };

  const handleFolderSelection = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const fileList = Array.from(files);
    e.target.value = "";

    const validFiles = fileList.filter((f) =>
      /\.(pdf|docx|txt|md)$/i.test(f.name) &&
      !f.type.startsWith("video/") &&
      !/\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(f.name)
    );

    if (validFiles.length === 0) {
      setUploadNotice("Please upload a folder containing PDF, TXT, DOCX, or MD files.");
      setCompanionStatus("comforting");
      return;
    }

    const folderName = (validFiles[0] as File & { webkitRelativePath?: string }).webkitRelativePath?.split("/")[0] ?? "Folder";
    await runUploadFlow(validFiles, folderName);
  };

  const [debugPanelOpen, setDebugPanelOpen] = useState(false);

  return (
    <section className="flex h-full flex-col overflow-hidden">
      <div className="flex min-h-0 flex-1 min-w-0">
        <div className="flex min-h-0 flex-1 flex-col min-w-0">
      <AnimatePresence>
        {reminderToast && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="flex shrink-0 items-center justify-between gap-4 border-b border-amber-200/60 bg-amber-50/95 px-4 py-3 text-slate-800 shadow-sm"
          >
            <span className="text-sm font-medium">{reminderToast.message}</span>
            <button
              type="button"
              onClick={() => setReminderToast(null)}
              className="rounded-full border border-amber-300/80 bg-white/80 px-3 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-100/80"
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* HITL checkpoint modal */}
      <AnimatePresence>
        {pendingHitl && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
            onClick={(e) => e.target === e.currentTarget && !hitlSubmitting && setPendingHitl(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[85vh] overflow-hidden flex flex-col border border-slate-200"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-5 overflow-y-auto flex-1">
                <h3 className="text-lg font-semibold text-slate-800 mb-2">Confirm</h3>
                <p className="text-slate-700 whitespace-pre-wrap mb-4">{pendingHitl.summary}</p>
                {pendingHitl.params && Object.keys(pendingHitl.params).length > 0 && (
                  <pre className="text-xs bg-slate-100 rounded-lg p-3 mb-4 overflow-x-auto text-slate-700">
                    {JSON.stringify(pendingHitl.params, null, 2)}
                  </pre>
                )}
                {pendingHitl.options && pendingHitl.options.length > 0 && (
                  <div className="space-y-2 mb-4">
                    <p className="text-sm font-medium text-slate-600">Choose an option:</p>
                    <div className="flex flex-col gap-2">
                      {pendingHitl.options.map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          disabled={hitlSubmitting}
                          onClick={() => handleHitlSelect(opt)}
                          className="text-left rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 hover:bg-slate-100 disabled:opacity-50"
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex gap-3 p-5 border-t border-slate-200 bg-slate-50/80">
                <button
                  type="button"
                  disabled={hitlSubmitting}
                  onClick={handleHitlApprove}
                  className="flex-1 rounded-xl bg-emerald-600 text-white px-4 py-2.5 text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50"
                >
                  {hitlSubmitting ? "Submitting…" : "Approve"}
                </button>
                <button
                  type="button"
                  disabled={hitlSubmitting}
                  onClick={handleHitlCancel}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

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
                initialGreetingFetchedRef.current = false;
                userHasSentMessageRef.current = false;
                clearConversation();
                setResponseId((r) => r + 1);
                setMood("neutral");
                setError(null);
                setValidationError(null);
                setUploadNotice(null);
                setPendingHitl(null);
                queueRef.current.clear();
                queueMessageIndexByStreamRef.current.clear();
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

      {/* Chat Area */}
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 p-4 sm:p-6 relative">
        <AnimatePresence>
          {isBubbleVisible && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.8, y: 20 }}
              className="absolute top-[10%] left-1/2 -translate-x-1/2 md:top-[15%] md:left-[55%] md:translate-x-0 w-[85vw] max-w-sm md:w-80 lg:w-96 origin-bottom md:origin-bottom-left z-20"
            >
               <img src="/assets/speech-bubble.svg" alt="Speech Bubble" className="w-full h-auto drop-shadow-xl opacity-90" />
               <div className="absolute inset-0 flex items-center justify-center p-6 pb-12 text-center">
                 <div className="max-h-full overflow-y-auto scrollbar-thin scrollbar-thumb-slate-400/50 pr-2">
                   <p className="text-slate-800 font-medium text-base leading-relaxed whitespace-pre-wrap">
                     <WordByWordText
                       content={messages.slice().reverse().find(m => m.role === 'assistant')?.content || "..."}
                       resetKey={responseId}
                     />
                   </p>
                 </div>
               </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Repeat Button */}
        {!isBubbleVisible && messages.some(m => m.role === 'assistant') && !loading && (
           <motion.button 
             initial={{ opacity: 0 }}
             animate={{ opacity: 1 }}
             onClick={repeatLastMessage}
             className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/20 px-6 py-3 text-sm font-bold text-white hover:bg-white/30 transition backdrop-blur-sm shadow-lg border border-white/30"
           >
             Repeat Last Message
           </motion.button>
        )}
      </div>

        {/* Server error / upload notice */}
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

        {/* Inline validation error (invalid input) */}
        {validationError && (
          <motion.div
            id="input-validation-error"
            role="alert"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-amber-300/80 bg-amber-50/90 px-4 py-2.5 text-sm text-amber-900 backdrop-blur-sm"
          >
            <p className="font-medium">{validationError}</p>
          </motion.div>
        )}

        {/* Input Area */}
        <form
          onSubmit={(e) => { e.preventDefault(); void send(); }}
          className="relative shrink-0 rounded-[2rem] border border-white/60 bg-white/40 p-2 shadow-lg shadow-indigo-500/5 backdrop-blur-md transition-all focus-within:bg-white/60 focus-within:shadow-indigo-500/10"
        >
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden" multiple onChange={handleFileSelection} />
          <input
            ref={(el) => {
              folderInputRef.current = el;
              if (el) {
                el.setAttribute("webkitdirectory", "");
                el.setAttribute("directory", "");
              }
            }}
            type="file"
            className="hidden"
            onChange={handleFolderSelection}
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="group flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/50 text-slate-600 transition hover:bg-white/80 hover:text-indigo-600"
              title="Upload files"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5 transition-transform group-hover:rotate-12" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 4v16m-8-8h16" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <button
              type="button"
              onClick={() => folderInputRef.current?.click()}
              className="group flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/50 text-slate-600 transition hover:bg-white/80 hover:text-indigo-600"
              title="Upload folder"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5 transition-transform group-hover:rotate-12" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <input
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                if (uploadNotice) setUploadNotice(null);
                if (validationError) setValidationError(null);
              }}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void send(); } }}
              placeholder="Ask your maid tutor anything..."
              className="h-10 flex-1 bg-transparent px-2 text-sm font-medium text-slate-800 placeholder:text-slate-500 focus:outline-none"
              aria-invalid={!!validationError}
              aria-describedby={validationError ? "input-validation-error" : undefined}
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

        {/* Debug panel - right side */}
        <div
          className={`flex shrink-0 flex-col border-l border-slate-200/80 bg-slate-900/95 overflow-hidden transition-[width] duration-200 ${debugPanelOpen ? "w-80" : "w-8"}`}
        >
          <div className="flex h-full min-w-0 flex-1 flex-col">
            <button
              type="button"
              onClick={() => setDebugPanelOpen((o) => !o)}
              className="flex shrink-0 items-center justify-between gap-2 border-b border-slate-600/80 bg-slate-800/90 px-2 py-2 text-left text-xs font-semibold text-slate-300 hover:bg-slate-700/90 min-h-9"
              aria-expanded={debugPanelOpen}
              title={debugPanelOpen ? "Close debug panel" : "Open debug panel"}
            >
              {debugPanelOpen ? (
                <>
                  <span>Debug</span>
                  <span className="text-slate-500 shrink-0">◀</span>
                </>
              ) : (
                <span className="w-full text-center text-[10px] uppercase tracking-wider" style={{ writingMode: "vertical-rl" }}>
                  Debug
                </span>
              )}
            </button>
            {debugPanelOpen && (
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <div className="shrink-0 space-y-1 border-b border-slate-600/60 bg-slate-800/50 px-2 py-2 text-[10px] text-slate-400">
                  <div>sessionId: {sessionId ?? "—"}</div>
                  <div>mood: {mood}</div>
                  <div>loading: {String(loading)}</div>
                  {error && <div className="text-rose-400">error: {error}</div>}
                  {validationError && <div className="text-amber-400">validation: {validationError}</div>}
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto p-2">
                  <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Messages</div>
                  <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-snug text-slate-300">
                    {messages.length === 0
                      ? "(none)"
                      : messages
                          .map((m, i) => `[${i}] ${m.role}: ${m.content}`)
                          .join("\n\n")}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
