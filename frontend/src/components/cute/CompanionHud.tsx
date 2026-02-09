import { motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAppStore } from "../../state/appStore";
import type { CompanionStatus } from "../../types/domain";

const statusLabel: Record<CompanionStatus, string> = {
  idle: "Idle",
  listening: "Listening",
  thinking: "Thinking",
  celebrating: "Yay!",
  comforting: "Comforting",
};

const statusTone: Record<CompanionStatus, string> = {
  idle: "from-white/75 to-lavender/55 text-indigo-700",
  listening: "from-aqua/70 to-sky/60 text-cyan-800",
  thinking: "from-butter/70 to-cream/60 text-amber-800",
  celebrating: "from-sakura/80 to-bubblegum/60 text-rose-800",
  comforting: "from-lilac/75 to-pink/60 text-violet-800",
};

export const CompanionHud = () => {
  const status = useAppStore((state) => state.companionStatus);
  const affection = useAppStore((state) => state.affection);
  const sessionStreak = useAppStore((state) => state.sessionStreak);
  const bumpAffection = useAppStore((state) => state.bumpAffection);
  const setCompanionStatus = useAppStore((state) => state.setCompanionStatus);
  const setMood = useAppStore((state) => state.setMood);

  const [burst, setBurst] = useState(0);
  const resetTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);

  const filledHearts = useMemo(() => Math.round((affection / 100) * 5), [affection]);

  const triggerSparkle = () => {
    setBurst((value) => value + 1);
  };

  const scheduleIdle = () => {
    if (resetTimeoutRef.current) {
      window.clearTimeout(resetTimeoutRef.current);
    }
    resetTimeoutRef.current = window.setTimeout(() => {
      setCompanionStatus("idle");
    }, 1000);
  };

  useEffect(
    () => () => {
      if (resetTimeoutRef.current) {
        window.clearTimeout(resetTimeoutRef.current);
      }
    },
    [],
  );

  const onHeadpat = () => {
    bumpAffection(1);
    setMood("happy");
    setCompanionStatus("celebrating");
    triggerSparkle();
    scheduleIdle();
  };

  const onCheer = () => {
    bumpAffection(2);
    setMood("excited");
    setCompanionStatus("celebrating");
    triggerSparkle();
    scheduleIdle();
  };

  return (
    <motion.aside
      className="relative w-[15.5rem] rounded-[1.8rem] border border-white/75 bg-white/35 p-3 shadow-glowPink backdrop-blur-[8px]"
      initial={{ opacity: 0, y: -14, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.36, ease: "easeOut" }}
    >
      <motion.div
        className={`rounded-full border border-white/80 bg-gradient-to-r px-3 py-1 text-xs font-bold uppercase tracking-[0.14em] ${statusTone[status]}`}
        animate={{
          scale: status === "celebrating" ? [1, 1.05, 1] : 1,
          boxShadow:
            status === "celebrating"
              ? ["0 0 0 rgba(0,0,0,0)", "0 0 22px rgba(255, 142, 197, 0.46)", "0 0 0 rgba(0,0,0,0)"]
              : "0 0 0 rgba(0,0,0,0)",
        }}
        transition={{ duration: 1.1, repeat: status === "celebrating" ? Infinity : 0 }}
      >
        Maid Status · {statusLabel[status]}
      </motion.div>

      <div className="mt-3 rounded-2xl border border-white/75 bg-white/45 p-3 shadow-sticker">
        <p className="text-[11px] font-extrabold uppercase tracking-[0.12em] text-slate-600">
          Affection
        </p>
        <div className="mt-1 flex items-center gap-1.5 text-lg text-bubblegum">
          {Array.from({ length: 5 }, (_, index) => (
            <span key={index} className={index < filledHearts ? "tiny-bounce" : "opacity-35"}>
              ❤
            </span>
          ))}
          <span className="ml-1 text-xs font-bold text-slate-700">{affection}%</span>
        </div>

        <p className="mt-3 text-[11px] font-extrabold uppercase tracking-[0.12em] text-slate-600">
          Session Streak
        </p>
        <div className="mt-1 flex items-center gap-2">
          <span className="rounded-full bg-butter/70 px-2 py-0.5 text-xs font-extrabold text-amber-800">
            {sessionStreak}
          </span>
          <span className="text-xs font-semibold text-slate-700">chat actions</span>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <motion.button
          type="button"
          onClick={onHeadpat}
          className="rounded-full border border-white/85 bg-gradient-to-r from-lavender/80 to-pink/75 px-3 py-2 text-xs font-extrabold uppercase tracking-[0.08em] text-indigo-900 shadow-glowAqua"
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.97 }}
        >
          Headpat
        </motion.button>
        <motion.button
          type="button"
          onClick={onCheer}
          className="rounded-full border border-white/85 bg-gradient-to-r from-sakura/80 to-bubblegum/75 px-3 py-2 text-xs font-extrabold uppercase tracking-[0.08em] text-rose-900 shadow-glowPink"
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.97 }}
        >
          Cheer
        </motion.button>
      </div>

      <div key={burst} className="pointer-events-none absolute inset-0 overflow-hidden rounded-[1.8rem]">
        {Array.from({ length: 6 }, (_, index) => (
          <motion.span
            key={`${burst}-${index}`}
            className="absolute left-1/2 top-1/2 text-xs text-bubblegum/80"
            initial={{ x: 0, y: 0, opacity: 0, scale: 0.6 }}
            animate={{
              x: [0, Math.cos((index / 6) * Math.PI * 2) * 42],
              y: [0, Math.sin((index / 6) * Math.PI * 2) * 28 - 8],
              opacity: [0, 1, 0],
              scale: [0.4, 1.2, 0.85],
            }}
            transition={{ duration: 0.85, ease: "easeOut" }}
          >
            ✦
          </motion.span>
        ))}
      </div>
    </motion.aside>
  );
};
