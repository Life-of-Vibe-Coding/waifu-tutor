"use client";

import { motion } from "framer-motion";
import { useAppStore } from "@/state/appStore";
import type { CharacterMood, CompanionStatus } from "@/types/domain";
import { Live2DCharacter } from "./Live2DCharacter";

const statusRing: Record<
  CompanionStatus,
  { scale: number[]; opacity: number[]; duration: number }
> = {
  idle: { scale: [1, 1.03, 1], opacity: [0.24, 0.36, 0.24], duration: 2.4 },
  listening: { scale: [0.96, 1.08, 0.96], opacity: [0.3, 0.82, 0.3], duration: 1.1 },
  thinking: { scale: [0.98, 1.04, 0.98], opacity: [0.32, 0.58, 0.32], duration: 0.8 },
  celebrating: { scale: [0.92, 1.15, 0.92], opacity: [0.45, 0.95, 0.45], duration: 0.7 },
  comforting: { scale: [1, 1.05, 1], opacity: [0.26, 0.56, 0.26], duration: 1.7 },
};

export const TutorPane = () => {
  const mood = useAppStore((s) => s.mood);
  const isListening = useAppStore((s) => s.isListening);
  const companionStatus = useAppStore((s) => s.companionStatus);
  const ringConfig = statusRing[companionStatus];

  return (
    <aside
      className="flex min-h-0 w-[min(100%,320px)] shrink-0 flex-col rounded-2xl border border-white/60 bg-white/25 shadow-[0_24px_60px_rgba(66,76,128,0.22)] backdrop-blur-sm sm:w-72 md:w-80 lg:w-96 xl:w-[26rem]"
      aria-label="Tutor character"
    >
      <div className="relative flex min-h-0 flex-1 flex-col items-center justify-end overflow-hidden rounded-2xl px-2 pb-2 pt-0">
        <motion.div
          className="absolute bottom-[8%] left-1/2 h-[70%] w-[85%] -translate-x-1/2 rounded-[999px] bg-gradient-to-t from-sakura/20 via-white/15 to-aqua/15 blur-lg"
          animate={{ opacity: [0.3, 0.7, 0.3] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute bottom-[10%] left-1/2 h-[65%] w-[78%] -translate-x-1/2 rounded-[999px] border border-white/65 bg-white/18"
          animate={{
            scale: isListening ? [0.95, 1.08, 0.95] : ringConfig.scale,
            opacity: ringConfig.opacity,
          }}
          transition={{ duration: ringConfig.duration, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute bottom-[12%] left-1/2 h-[54%] w-[62%] -translate-x-1/2 rounded-[999px] border border-white/55 bg-white/12"
          animate={{ scale: [1, 1.06, 1], opacity: [0.22, 0.5, 0.22] }}
          transition={{ duration: 1.6, repeat: companionStatus === "celebrating" ? Infinity : 0 }}
        />
        <motion.div
          className="relative h-full w-full max-w-[280px] md:max-w-[320px] lg:max-w-[360px] xl:max-w-[400px]"
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut" }}
        >
          <Live2DCharacter mood={mood} status={companionStatus} />
        </motion.div>
      </div>
    </aside>
  );
};
