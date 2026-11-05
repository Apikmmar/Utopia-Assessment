import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e/live",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 240_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  outputDir: "../tmp/e2e-live/artifacts",
  use: { baseURL: "http://localhost:5174", trace: "off", screenshot: "only-on-failure" },
  projects: [{ name: "live-chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev -- --config vite.live.config.ts --strictPort",
    url: "http://localhost:5174",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
