"use client";

import { motion } from "framer-motion";
import { FloatingDecor } from "./cute/FloatingDecor";

export const PageBackground = () => {
  return (
    <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <FloatingDecor />
      <motion.div
        className="absolute -left-20 top-10 h-72 w-72 rounded-full bg-sakura/40 blur-2xl"
        animate={{ x: [0, 24, 0], y: [0, -16, 0], scale: [1, 1.08, 1] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -right-16 top-14 h-80 w-80 rounded-full bg-aqua/40 blur-2xl"
        animate={{ x: [0, -28, 0], y: [0, 18, 0], scale: [1, 1.12, 1] }}
        transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-6 left-1/2 h-56 w-[26rem] -translate-x-1/2 rounded-[999px] bg-butter/55 blur-2xl"
        animate={{ scale: [1, 1.08, 1], opacity: [0.65, 0.9, 0.65] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
};
