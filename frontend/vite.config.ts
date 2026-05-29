import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend. SSE-safe: the dev proxy streams
// text/event-stream without buffering so chat tokens arrive incrementally.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        // ensure SSE is not buffered
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            if (proxyRes.headers["content-type"]?.includes("text/event-stream")) {
              proxyRes.headers["x-accel-buffering"] = "no";
            }
          });
        },
      },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test-setup.ts",
    // e2e/ is Playwright, not Vitest — keep it out of the unit run.
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
  },
});
