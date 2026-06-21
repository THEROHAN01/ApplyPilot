/**
 * @module e2e/auth.spec
 * @description Browser E2E for the authentication flow: login redirect,
 *              unauthenticated guard, and invalid-credentials error surfacing.
 * @dependencies @playwright/test
 */
import { expect, test } from "@playwright/test";
import { credentials, loginViaUI, seedUser } from "./helpers";

test.beforeAll(async () => {
  await seedUser();
});

test("login redirects to the dashboard", async ({ page }) => {
  await loginViaUI(page);
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});

test("visiting a protected route unauthenticated redirects to /login", async ({ page }) => {
  await page.context().clearCookies();
  await page.goto("/dashboard");
  await page.waitForURL("**/login");
  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
});

test("invalid credentials show an inline error", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("you@example.com").fill(credentials.email);
  await page.getByPlaceholder("Password").fill("definitely-wrong-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText("Invalid email or password.")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});

test("signup page renders and links back to login", async ({ page }) => {
  await page.goto("/signup");
  await expect(page.getByPlaceholder("you@example.com")).toBeVisible();
  await expect(page.getByPlaceholder("Password (min 8 chars)")).toBeVisible();
  await expect(page.getByRole("button", { name: /create account/i })).toBeVisible();
  await page.getByRole("link", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/login$/);
});
