import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

type DecorType = "star" | "heart" | "petal";

interface DecorItem {
  id: number;
  type: DecorType;
  left: number;
  top: number;
  size: number;
  duration: number;
  delay: number;
}

const glyph: Record<DecorType, string> = {
  star: "✦",
  heart: "❤",
  petal: "❀",
};

const tone: Record<DecorType, string> = {
  star: "text-butter/85",
  heart: "text-bubblegum/75",
  petal: "text-lavender/70",
};

const seeded = (seed: number) => {
  const value = Math.sin(seed * 43758.5453) * 10000;
  return value - Math.floor(value);
};

export const FloatingDecor = () => {
  const [width, setWidth] = useState<number>(
    typeof window !== "undefined" ? window.innerWidth : 1280,
  );

  useEffect(() => {
    const handleResize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const items = useMemo<DecorItem[]>(() => {
    const count = width < 640 ? 8 : width < 1024 ? 12 : 18;

    return Array.from({ length: count }, (_, index) => {
      const kindIndex = Math.floor(seeded(index + 4) * 3);
      const type = (["star", "heart", "petal"] as DecorType[])[kindIndex];
      return {
        id: index,
        type,
        left: 4 + seeded(index * 2.1) * 92,
        top: 5 + seeded(index * 3.4 + 2) * 88,
        size: 12 + Math.floor(seeded(index * 5.2 + 1) * 11),
        duration: 4.2 + seeded(index * 6.3 + 9) * 4.8,
        delay: seeded(index * 8.7 + 11) * 2.4,
      };
    });
  }, [width]);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {items.map((item) => (
        <motion.span
          key={item.id}
          className={`absolute select-none ${tone[item.type]}`}
          style={{
            left: `${item.left}%`,
            top: `${item.top}%`,
            fontSize: `${item.size}px`,
          }}
          animate={{
            y: [0, -10, 0],
            x: [0, item.id % 2 === 0 ? 7 : -7, 0],
            opacity: [0.28, 0.9, 0.35],
            scale: [0.85, 1.16, 0.9],
            rotate: [0, item.id % 2 === 0 ? 15 : -15, 0],
          }}
          transition={{
            duration: item.duration,
            delay: item.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          {glyph[item.type]}
        </motion.span>
      ))}
    </div>
  );
};
