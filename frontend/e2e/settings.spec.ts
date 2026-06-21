/**
 * @module e2e/settings.spec
 * @description Browser E2E for the settings page resume upload: uploading a
 *              PDF surfaces the file in the uploaded-resumes list.
 *
 *              The UI has no toast component in Phase 1 — upload success is
 *              shown by the file appearing in the list and the button
 *              returning from its "Uploading…" state, so that is what we assert.
 * @dependencies @playwright/test
 */
import path from "node:path";

import { expect, test } from "@playwright/test";
import { loginViaUI, seedUser } from "./helpers";

const RESUME_PATH = path.join(__dirname, "fixtures", "sample_resume.pdf");

test.beforeAll(async () => {
  await seedUser();
});

test.beforeEach(async ({ page }) => {
  await loginViaUI(page);
});

test("settings page renders the resume section", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByText("Resume", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /upload resume/i })).toBeVisible();
});

test("uploading a PDF adds it to the resume list", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();

  // The file input is hidden and triggered via a button; set files directly.
  await page.locator('input[type="file"]').setInputFiles(RESUME_PATH);

  // Upload success: the filename appears in the list and no error is shown.
  await expect(page.getByText("sample_resume.pdf").first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("Upload failed.")).toHaveCount(0);
});
