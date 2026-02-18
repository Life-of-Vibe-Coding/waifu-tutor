/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const devProxyTarget = process.env.VITE_DEV_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  publicDir: path.resolve(__dirname, "./public"),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: devProxyTarget,
        changeOrigin: true,
      },
      "/health": {
        target: devProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
