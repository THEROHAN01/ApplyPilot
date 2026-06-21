/**
 * @module e2e/applications.spec
 * @description Browser E2E for the applications page: kanban columns render,
 *              the table-view toggle works, and the page loads error-free.
 * @dependencies @playwright/test
 */
import { expect, test } from "@playwright/test";
import { collectConsoleErrors, loginViaUI, seedApplication, seedUser } from "./helpers";

test.beforeAll(async () => {
  await seedUser();
  await seedApplication();
});

test.beforeEach(async ({ page }) => {
  await loginViaUI(page);
});

test("applications page renders kanban columns with no console errors", async ({ page }) => {
  const errors = collectConsoleErrors(page);
  await page.goto("/applications");
  await expect(page.getByRole("heading", { name: "Applications" })).toBeVisible();
  await expect(page.getByText("Loading…")).toHaveCount(0, { timeout: 10_000 });
  await expect(page.getByText("Failed to load applications.")).toHaveCount(0);

  // With an empty pipeline the empty-state shows; otherwise the kanban columns do.
  const emptyState = page.getByText("No applications yet");
  const pendingColumn = page.getByText(/^pending \(\d+\)$/);
  await emptyState.or(pendingColumn).first().waitFor();
  expect(errors, `console errors: ${errors.join("\n")}`).toEqual([]);
});

test("table view toggle switches to the table layout", async ({ page }) => {
  await page.goto("/applications");
  await expect(page.getByRole("heading", { name: "Applications" })).toBeVisible();
  // Wait for useApplications data to settle (kanban renders) before toggling —
  // until data loads, neither view renders, so a premature click is a no-op.
  await expect(page.getByText(/^pending \(\d+\)$/)).toBeVisible({ timeout: 15_000 });

  await page.getByRole("button", { name: "Table" }).click();
  // The <table> with its header row is unique to the table view.
  const table = page.locator("table");
  await expect(table).toBeVisible();
  const thead = table.locator("thead");
  for (const header of ["Role", "Company", "Status", "Created"]) {
    await expect(thead).toContainText(header);
  }
  // Switching back to kanban removes the table from the DOM.
  await page.getByRole("button", { name: "Kanban" }).click();
  await expect(table).toHaveCount(0);
});
