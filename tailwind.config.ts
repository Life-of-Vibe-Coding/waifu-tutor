import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#fff9f4",
        panel: "#fff8fd",
        accent: "#ff6f9f",
        ink: "#1f2441",
        calm: "#4da1c7",
        pink: "#ffd8e7",
        sky: "#d9efff",
        cream: "#fff6dc",
        mint: "#dbf6ec",
        lilac: "#e8ddff",
        sakura: "#ffb6d8",
        bubblegum: "#ff89c1",
        cotton: "#fff8ff",
        aqua: "#9de7ff",
        butter: "#ffe7a3",
        lavender: "#c8b7ff",
      },
      fontFamily: {
        display: ["'Quicksand'", "sans-serif"],
        body: ["'Nunito'", "sans-serif"],
      },
      boxShadow: {
        soft: "0 14px 40px rgba(71, 83, 128, 0.16)",
        glowPink: "0 0 0 1px rgba(255, 183, 220, 0.7), 0 20px 45px rgba(244, 109, 176, 0.28)",
        glowAqua: "0 0 0 1px rgba(157, 231, 255, 0.7), 0 18px 42px rgba(78, 175, 226, 0.24)",
        sticker: "0 10px 26px rgba(95, 88, 136, 0.22)",
      },
    },
  },
  plugins: [],
} satisfies Config;
