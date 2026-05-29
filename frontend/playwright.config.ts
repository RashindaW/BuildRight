import { defineConfig } from "@playwright/test";

// E2E config. Requires: backend on :8000 (seeded) and `npm run dev` on :5173,
// OR set PLAYWRIGHT_BASE_URL. Install once with: npm i -D @playwright/test && npx playwright install chromium
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173",
    headless: true,
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : { command: "npm run dev", url: "http://localhost:5173", reuseExistingServer: true },
});
