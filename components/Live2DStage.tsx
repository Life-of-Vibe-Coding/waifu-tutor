"use client";

import { motion } from "framer-motion";
import { useAppStore } from "@/state/appStore";
import type { CharacterMood, CompanionStatus } from "@/types/domain";
import { FloatingDecor } from "./cute/FloatingDecor";
import { Live2DCharacter } from "./Live2DCharacter";

const statusRing: Record<CompanionStatus, { scale: number[]; opacity: number[]; duration: number }> = {
  idle: { scale: [1, 1.03, 1], opacity: [0.24, 0.36, 0.24], duration: 2.4 },
  listening: { scale: [0.96, 1.08, 0.96], opacity: [0.3, 0.82, 0.3], duration: 1.1 },
  thinking: { scale: [0.98, 1.04, 0.98], opacity: [0.32, 0.58, 0.32], duration: 0.8 },
  celebrating: { scale: [0.92, 1.15, 0.92], opacity: [0.45, 0.95, 0.45], duration: 0.7 },
  comforting: { scale: [1, 1.05, 1], opacity: [0.26, 0.56, 0.26], duration: 1.7 },
};

export const Live2DStage = () => {
  const mood = useAppStore((state) => state.mood);
  const isListening = useAppStore((state) => state.isListening);
  const companionStatus = useAppStore((state) => state.companionStatus);
  const ringConfig = statusRing[companionStatus];

  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <FloatingDecor />
      <motion.div
        className="absolute -left-20 top-10 h-72 w-72 rounded-full bg-sakura/45 blur-2xl"
        animate={{ x: [0, 24, 0], y: [0, -16, 0], scale: [1, 1.08, 1] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -right-16 top-14 h-80 w-80 rounded-full bg-aqua/45 blur-2xl"
        animate={{ x: [0, -28, 0], y: [0, 18, 0], scale: [1, 1.12, 1] }}
        transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-6 left-1/2 h-56 w-[26rem] -translate-x-1/2 rounded-[999px] bg-butter/65 blur-2xl"
        animate={{ scale: [1, 1.08, 1], opacity: [0.65, 0.95, 0.65] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="absolute inset-0 flex items-end justify-center">
        <div className="relative h-[80vh] w-[min(92vw,840px)]">
          <motion.div
            className="absolute bottom-[4%] left-1/2 h-[72%] w-[74%] -translate-x-1/2 rounded-[999px] bg-gradient-to-t from-sakura/28 via-white/20 to-aqua/20 blur-lg"
            animate={{ opacity: [0.3, 0.75, 0.3] }}
            transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute bottom-[5%] left-1/2 h-[68%] w-[70%] -translate-x-1/2 rounded-[999px] border border-white/70 bg-white/16"
            animate={{
              scale: isListening ? [0.95, 1.09, 0.95] : ringConfig.scale,
              opacity: ringConfig.opacity,
            }}
            transition={{ duration: ringConfig.duration, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute bottom-[6%] left-1/2 h-[57%] w-[58%] -translate-x-1/2 rounded-[999px] border border-white/65 bg-white/12"
            animate={{ scale: [1, 1.08, 1], opacity: [0.22, 0.62, 0.22] }}
            transition={{ duration: 1.6, repeat: companionStatus === "celebrating" ? Infinity : 0 }}
          />
          <motion.div
            className="absolute inset-0"
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut" }}
          >
            <Live2DCharacter mood={mood} status={companionStatus} />
          </motion.div>
        </div>
      </div>
    </div>
  );
};
