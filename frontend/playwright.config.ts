/**
 * @module playwright.config
 * @description Playwright browser E2E configuration for the ApplyPilot
 *              frontend. Tests live in ./e2e and run against a Next.js dev
 *              server on :3000 (started automatically unless one is already
 *              running). The backend API is expected on :8000 — in CI it is
 *              brought up via docker-compose before the Playwright job runs.
 * @dependencies @playwright/test
 */
import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // reuseExistingServer is true everywhere: in CI the frontend is served by
  // docker-compose on :3000, so Playwright reuses it rather than racing for the
  // port; locally it reuses a running `npm run dev` or starts one if absent.
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 120_000,
    env: { NEXT_PUBLIC_API_URL: API_URL },
  },
});
