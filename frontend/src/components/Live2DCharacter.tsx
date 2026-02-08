import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import type { CharacterMood } from "../types/domain";

interface Props {
  mood: CharacterMood;
}

type Live2DBridgeMessage = {
  source: "waifu-tutor";
  type: "WAIFU_TUTOR_MOOD";
  mood: CharacterMood;
  timestamp: string;
};

const moodColor: Record<CharacterMood, string> = {
  neutral: "from-slate-200 to-slate-300",
  happy: "from-emerald-200 to-emerald-300",
  encouraging: "from-amber-200 to-amber-300",
  sad: "from-blue-200 to-blue-300",
  excited: "from-rose-200 to-orange-200",
};

const moodText: Record<CharacterMood, string> = {
  neutral: "Ready to study",
  happy: "Nice work",
  encouraging: "Keep going",
  sad: "Try again",
  excited: "Amazing",
};

export const Live2DCharacter = ({ mood }: Props) => {
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
        className="relative h-full min-h-[620px] w-full overflow-hidden rounded-3xl border border-white/80 bg-white shadow-soft"
        animate={{ y: [0, -4, 0] }}
        transition={{ duration: 3.8, repeat: Infinity, ease: "easeInOut" }}
      >
        <iframe
          ref={iframeRef}
          title="Live2D character"
          src="/live2d-demo/index.html"
          className="h-full w-full border-0"
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
        <div className="pointer-events-none absolute bottom-2 left-2 rounded bg-white/90 px-2 py-1 text-[11px] font-semibold text-slate-700">
          {moodText[mood]}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className={`relative h-full min-h-[620px] w-full overflow-hidden rounded-3xl bg-gradient-to-br ${moodColor[mood]} shadow-soft`}
      animate={{ y: [0, -4, 0], rotate: [0, 0.5, 0] }}
      transition={{ duration: 3.8, repeat: Infinity, ease: "easeInOut" }}
    >
      <div className="absolute inset-x-0 top-5 mx-auto h-28 w-28 rounded-full bg-white/65" />
      <div className="absolute bottom-3 left-3 rounded-xl bg-white/80 px-3 py-2 text-sm font-semibold text-ink">
        {moodText[mood]}
      </div>
      <div className="absolute right-3 top-3 rounded bg-white/80 px-2 py-1 text-xs font-medium text-calm">
        Live2D files missing
      </div>
    </motion.div>
  );
};
