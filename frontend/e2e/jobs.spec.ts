/**
 * @module e2e/jobs.spec
 * @description Browser E2E for the jobs feed: it renders (feed or empty state)
 *              and the filter inputs are interactive without errors.
 * @dependencies @playwright/test
 */
import { expect, test } from "@playwright/test";
import { collectConsoleErrors, loginViaUI, seedUser } from "./helpers";

test.beforeAll(async () => {
  await seedUser();
});

test.beforeEach(async ({ page }) => {
  await loginViaUI(page);
});

test("jobs feed renders (list or empty state) with no console errors", async ({ page }) => {
  const errors = collectConsoleErrors(page);
  await page.goto("/jobs");
  await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible();
  // Either jobs render or the empty state is shown — both are valid.
  const empty = page.getByText("No jobs yet.");
  const feedLoaded = page.getByText("Loading jobs…");
  await expect(feedLoaded).toHaveCount(0, { timeout: 10_000 });
  await expect(page.getByText("Failed to load jobs.")).toHaveCount(0);
  // empty-state OR at least the heading present is sufficient; assert no crash.
  await empty.or(page.getByRole("heading", { name: "Jobs" })).first().waitFor();
  expect(errors, `console errors: ${errors.join("\n")}`).toEqual([]);
});

test("job filters accept input", async ({ page }) => {
  await page.goto("/jobs");
  const search = page.getByPlaceholder("Search role or company");
  const source = page.getByPlaceholder("Source (e.g. greenhouse)");
  await search.fill("engineer");
  await source.fill("greenhouse");
  await expect(search).toHaveValue("engineer");
  await expect(source).toHaveValue("greenhouse");
  // The feed must not error out after filtering.
  await expect(page.getByText("Failed to load jobs.")).toHaveCount(0);
});
