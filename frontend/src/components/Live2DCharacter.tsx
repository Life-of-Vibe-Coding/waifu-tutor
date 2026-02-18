import { motion } from "framer-motion";
import React, { useEffect, useRef, useState } from "react";
import type { CharacterMood, CompanionStatus } from "@/types/domain";
import { CompanionHud } from "./cute/CompanionHud";

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



const moodShadow: Record<CharacterMood, string> = {
  neutral: "bg-sky-100/45",
  happy: "bg-pink-100/45",
  encouraging: "bg-amber-100/45",
  sad: "bg-blue-100/45",
  excited: "bg-fuchsia-100/45",
  gentle: "bg-purple-100/45",
};

export const Live2DCharacter = ({ mood, status = "idle" }: Props) => {
  const [sampleAvailable, setSampleAvailable] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  useEffect(() => {
    let mounted = true;
    void fetch("/live2d-demo/index.html", { method: "GET" })
      .then(async (response) => {
        if (!mounted) return;
        if (!response.ok) {
          setSampleAvailable(false);
          return;
        }
        const html = await response.text();
        // Check for specific markers of the demo page to ensure we didn't get the app shell (SPA fallback)
        const isDemoPage = html.includes('id="app"') && html.includes('live2d-app.js');
        setSampleAvailable(isDemoPage);
      })
      .catch((err) => {
        console.error("Failed to check Live2D demo page:", err);
        if (mounted) setSampleAvailable(false);
      });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (!sampleAvailable || !iframeRef.current?.contentWindow) return;
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
        <div className={`pointer-events-none absolute inset-x-0 bottom-[2%] mx-auto h-[16%] w-[52%] rounded-[999px] blur-xl transition-colors duration-1000 ${moodShadow[mood]}`} />
        <iframe
          ref={iframeRef}
          title="Live2D character"
          src="/live2d-demo/index.html"
          className="h-full w-full border-0 bg-transparent"
          style={{ backgroundColor: "transparent" }}
          allowTransparency={true}
          onLoad={() => {
            if (!iframeRef.current?.contentWindow) return;
            const payload: Live2DBridgeMessage = {
              source: "waifu-tutor",
              type: "WAIFU_TUTOR_MOOD",
              mood,
              timestamp: new Date().toISOString(),
            };
            iframeRef.current.contentWindow.postMessage(payload, window.location.origin);
          }}
        />
        <CompanionHud className="absolute left-4 top-4 z-10" />
        {status === "celebrating" && (
          <motion.div
            className="pointer-events-none absolute inset-0 rounded-full border border-bubblegum/30"
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
      className="relative h-full w-full overflow-hidden"
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

      <CompanionHud className="absolute left-4 top-4 z-10" />

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
