import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import type { CharacterMood, CompanionStatus } from "../types/domain";

interface Props {
  mood: CharacterMood;
  status?: CompanionStatus;
}

type Live2DBridgeMessage = {
  source: "waifu-tutor";
  type: "WAIFU_TUTOR_MOOD";
  mood: CharacterMood;
  timestamp: string;
};

const moodColor: Record<CharacterMood, string> = {
  neutral: "from-white/50 via-slate-100/45 to-sky-100/45",
  happy: "from-rose-100/55 via-pink-100/50 to-fuchsia-100/45",
  encouraging: "from-amber-100/55 via-orange-100/50 to-yellow-100/45",
  sad: "from-blue-100/55 via-cyan-100/50 to-sky-100/45",
  excited: "from-fuchsia-100/55 via-rose-100/50 to-orange-100/45",
};

const moodText: Record<CharacterMood, string> = {
  neutral: "Ready to study",
  happy: "Nice work",
  encouraging: "Keep going",
  sad: "Try again",
  excited: "Amazing",
};

const statusText: Record<CompanionStatus, string> = {
  idle: "Ready~",
  listening: "Listening ♪",
  thinking: "Thinking...",
  celebrating: "Yay!!",
  comforting: "It's okay",
};

const statusTone: Record<CompanionStatus, string> = {
  idle: "from-white/70 to-lavender/50 text-indigo-700",
  listening: "from-aqua/70 to-sky/55 text-cyan-800",
  thinking: "from-butter/75 to-cream/55 text-amber-800",
  celebrating: "from-sakura/80 to-bubblegum/65 text-rose-800",
  comforting: "from-lilac/75 to-pink/55 text-violet-800",
};

export const Live2DCharacter = ({ mood, status = "idle" }: Props) => {
  const [sampleAvailable, setSampleAvailable] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  useEffect(() => {
    let mounted = true;
    void fetch("/live2d-demo/index.html", { method: "GET" })
      .then(async (response) => {
        if (!mounted) {
          return;
        }
        if (!response.ok) {
          setSampleAvailable(false);
          return;
        }

        const html = await response.text();
        // Vite dev server can return app shell HTML for unknown paths.
        // Detect that case and keep fallback renderer active.
        const looksLikeWaifuShell = html.includes("<title>Waifu Tutor</title>");
        setSampleAvailable(!looksLikeWaifuShell);
      })
      .catch(() => {
        if (mounted) {
          setSampleAvailable(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!sampleAvailable || !iframeRef.current?.contentWindow) {
      return;
    }

    const payload: Live2DBridgeMessage = {
      source: "waifu-tutor",
      type: "WAIFU_TUTOR_MOOD",
      mood,
      timestamp: new Date().toISOString(),
    };
    iframeRef.current.contentWindow.postMessage(payload, window.location.origin);
  }, [mood, sampleAvailable]);

  if (sampleAvailable) {
    return (
      <motion.div
        className="relative h-full w-full overflow-hidden"
        animate={{ rotateZ: [0, 0.35, 0, -0.3, 0] }}
        transition={{ duration: 7.8, repeat: Infinity, ease: "easeInOut" }}
      >
        <div className="pointer-events-none absolute inset-x-0 bottom-[2%] mx-auto h-[16%] w-[52%] rounded-[999px] bg-sky-100/45 blur-xl" />
        <iframe
          ref={iframeRef}
          title="Live2D character"
          src="/live2d-demo/index.html"
          className="h-full w-full border-0 bg-transparent"
          onLoad={() => {
            if (!iframeRef.current?.contentWindow) {
              return;
            }
            const payload: Live2DBridgeMessage = {
              source: "waifu-tutor",
              type: "WAIFU_TUTOR_MOOD",
              mood,
              timestamp: new Date().toISOString(),
            };
            iframeRef.current.contentWindow.postMessage(payload, window.location.origin);
          }}
        />
        <motion.div
          className="pointer-events-none absolute left-4 top-4 rounded-full border border-white/75 bg-white/36 px-3 py-1 text-[11px] font-extrabold uppercase tracking-[0.1em] text-slate-700"
          animate={{ y: [0, -3, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          {statusText[status]}
        </motion.div>
        <div className="pointer-events-none absolute bottom-5 left-4 rounded-full border border-white/65 bg-white/36 px-3 py-1.5 text-[11px] font-semibold text-slate-700">
          {moodText[mood]}
        </div>
        {status === "celebrating" && (
          <motion.div
            className="pointer-events-none absolute inset-0 rounded-full border border-bubblegum/55"
            initial={{ opacity: 0.7, scale: 0.88 }}
            animate={{ opacity: 0, scale: 1.16 }}
            transition={{ duration: 0.65, ease: "easeOut" }}
          />
        )}
      </motion.div>
    );
  }

  return (
    <motion.div
      className={`relative h-full w-full overflow-hidden bg-gradient-to-br ${moodColor[mood]}`}
      animate={{ y: [0, -9, 0], rotate: [0, 0.8, 0, -0.6, 0] }}
      transition={{ duration: 6.2, repeat: Infinity, ease: "easeInOut" }}
    >
      <motion.div
        className="absolute inset-x-[26%] top-[10%] h-20 rounded-full bg-white/55 blur-lg"
        animate={{ scale: [1, 1.18, 1], opacity: [0.5, 0.85, 0.5] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="absolute bottom-[22%] left-1/2 h-[58%] w-[40%] -translate-x-1/2 rounded-[44%_44%_40%_40%] border border-white/55 bg-white/35 shadow-[0_20px_40px_rgba(76,90,138,0.18)]" />
      <div className="absolute left-1/2 top-[24%] h-[15%] w-[19%] -translate-x-1/2 rounded-full border border-white/60 bg-white/45" />
      <div className="absolute bottom-8 left-4 rounded-full border border-white/65 bg-white/35 px-3 py-1.5 text-sm font-semibold text-slate-800">
        {moodText[mood]}
      </div>
      <motion.div
        className={`absolute left-4 top-4 rounded-full border border-white/75 bg-gradient-to-r px-3 py-1 text-xs font-extrabold uppercase tracking-[0.08em] ${statusTone[status]}`}
        animate={{ y: [0, -3, 0] }}
        transition={{ duration: 2.1, repeat: Infinity, ease: "easeInOut" }}
      >
        {statusText[status]}
      </motion.div>
      <div className="absolute right-4 top-4 rounded-full border border-white/65 bg-white/35 px-3 py-1.5 text-xs font-semibold tracking-wide text-calm">
        Live2D files missing
      </div>
      {status === "celebrating" && (
        <motion.div
          className="pointer-events-none absolute inset-4 rounded-[40%_40%_45%_45%] border border-bubblegum/55"
          initial={{ opacity: 0.7, scale: 0.9 }}
          animate={{ opacity: 0, scale: 1.08 }}
          transition={{ duration: 0.65, ease: "easeOut" }}
        />
      )}
    </motion.div>
  );
};
