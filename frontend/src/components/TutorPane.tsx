import { motion } from "framer-motion";
import { useAppStore } from "@/state/appStore";
import React, { useEffect, useState } from "react";
import type { CompanionStatus, CharacterMood } from "@/types/domain";
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

const moodGlow: Record<CharacterMood, string> = {
  neutral: "from-sky-200/30",
  happy: "from-pink-200/30",
  encouraging: "from-amber-200/30",
  sad: "from-blue-200/30",
  excited: "from-fuchsia-200/30",
  gentle: "from-purple-200/30",
};

export const TutorPane = () => {
  const mood = useAppStore((s) => s.mood);
  const isListening = useAppStore((s) => s.isListening);
  const companionStatus = useAppStore((s) => s.companionStatus);
  const ringConfig = statusRing[companionStatus];

  /* Wandering Logic */
  const [wanderPos, setWanderPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (companionStatus !== "idle") {
      setWanderPos({ x: 0, y: 0 });
      return;
    }

    const moveCharacter = () => {
      // Wander within a safe range (e.g., +/- 15% of parent container)
      // Since we can't easily get parent dimensions in pixels without ref, we use percentage strings or small pixel values.
      // Let's use pixel values assuming a standard container size, or small percentages.
      const rangeX = 40; // px
      const rangeY = 20; // px
      const x = (Math.random() - 0.5) * 2 * rangeX;
      const y = (Math.random() - 0.5) * 2 * rangeY;
      setWanderPos({ x, y });
    };

    // Move immediately then periodically
    moveCharacter();
    const interval = setInterval(moveCharacter, 4500 + Math.random() * 2000);
    return () => clearInterval(interval);
  }, [companionStatus]);


  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden">
      {/* Ambient Background Glow */}
      <motion.div
        className={`absolute bottom-0 left-1/2 h-[70%] w-full -translate-x-1/2 bg-gradient-to-t via-white/5 to-transparent blur-3xl transition-colors duration-1000 ${moodGlow[mood]}`}
        animate={{ opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Status Ring 1 (Subtle Ripple) */}
      <motion.div
        className="absolute bottom-[12%] left-1/2 h-[50%] w-[80%] -translate-x-1/2 rounded-[999px] border border-white/20 shadow-[0_0_40px_rgba(255,255,255,0.1)]"
        animate={{
          scale: isListening ? [0.95, 1.05, 0.95] : ringConfig.scale,
          opacity: [0.1, 0.3, 0.1],
        }}
        transition={{ duration: ringConfig.duration, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Status Ring 2 (Inner Glow) */}
      <motion.div
        className="absolute bottom-[15%] left-1/2 h-[40%] w-[65%] -translate-x-1/2 rounded-[999px] bg-white/10 blur-xl"
        animate={{ scale: [1, 1.04, 1], opacity: [0.2, 0.4, 0.2] }}
        transition={{ duration: 2, repeat: companionStatus === "celebrating" ? Infinity : 0 }}
      />

      {/* Character Container - Wandering Layer */}
      <motion.div
        className="relative z-10 h-full w-full"
        animate={{
          x: wanderPos.x,
          y: wanderPos.y,
        }}
        transition={{
          duration: companionStatus === "idle" ? 3.5 : 0.8,
          ease: "easeInOut",
        }}
      >
        {/* Character Container - Breathing Layer */}
        <motion.div
          className="h-full w-full"
          animate={{
            y: [0, -4, 0],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <Live2DCharacter mood={mood} status={companionStatus} />
        </motion.div>
      </motion.div>
    </div>
  );
};
