/**
 * @module e2e/helpers
 * @description Shared helpers for browser E2E specs: seeding a backend user via
 *              the API and logging in through the real UI. Credentials come from
 *              the E2E_TEST_EMAIL / E2E_TEST_PASSWORD env vars (never hardcoded).
 *
 *              Note: Phase 1 exposes no delete-user endpoint, so per-spec API
 *              teardown is not possible. seedUser() is therefore idempotent — a
 *              409 (already registered) is treated as success — and specs reuse
 *              a stable test account rather than leaking unique users each run.
 * @dependencies @playwright/test
 */
import { expect, request, type Page } from "@playwright/test";

const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

export const credentials = {
  email: process.env.E2E_TEST_EMAIL ?? "e2e@applypilot.dev",
  password: process.env.E2E_TEST_PASSWORD ?? "E2eTest1234!",
};

/**
 * Ensure the test user exists in the backend. Idempotent: signup returning
 * 409 (already registered) is considered success.
 */
export async function seedUser(): Promise<void> {
  const ctx = await request.newContext({ baseURL: API_URL });
  const resp = await ctx.post("/auth/signup", {
    data: { email: credentials.email, password: credentials.password, name: "E2E User" },
    failOnStatusCode: false,
  });
  expect(
    [201, 409].includes(resp.status()),
    `Unexpected signup status ${resp.status()}: ${await resp.text()}`,
  ).toBeTruthy();
  await ctx.dispose();
}

/**
 * Ensure the test user has at least one application (creates a job + an
 * application via the API). Makes kanban/table assertions deterministic
 * regardless of prior state. Idempotent enough for repeated runs.
 */
export async function seedApplication(): Promise<void> {
  const ctx = await request.newContext({ baseURL: API_URL });
  const login = await ctx.post("/auth/login", {
    data: { email: credentials.email, password: credentials.password },
  });
  expect(login.ok(), `login failed: ${await login.text()}`).toBeTruthy();
  const token = (await login.json()).access_token as string;
  const headers = { Authorization: `Bearer ${token}` };

  const job = await ctx.post("/jobs", {
    headers,
    data: { source: "manual", company: "E2E Corp", role: "E2E Engineer" },
  });
  expect(job.status()).toBe(201);
  const jobId = (await job.json()).id as string;

  const app = await ctx.post("/applications", { headers, data: { job_id: jobId } });
  expect(app.status()).toBe(201);
  await ctx.dispose();
}

/** Log in through the UI and wait for the dashboard to load. */
export async function loginViaUI(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByPlaceholder("you@example.com").fill(credentials.email);
  await page.getByPlaceholder("Password").fill(credentials.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL("**/dashboard");
}

/** Fail a test if any browser console error is emitted while attached. */
export function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(err.message));
  return errors;
}
