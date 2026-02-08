import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#f8f5ef",
        panel: "#fffdf7",
        accent: "#d84f38",
        ink: "#1f1f1f",
        calm: "#4a7b73",
      },
      fontFamily: {
        display: ["'Fraunces'", "serif"],
        body: ["'Work Sans'", "sans-serif"],
      },
      boxShadow: {
        soft: "0 12px 30px rgba(30, 30, 30, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
