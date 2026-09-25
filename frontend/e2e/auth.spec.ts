import { expect, test } from "@playwright/test";
import { PASSWORD, registerUser } from "./helpers";

test("protected pages redirect to login", async ({ page }) => {
  await page.goto("/history");
  await expect(page).toHaveURL(/\/login\?next=%2Fhistory/);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
});

test("register, sign out and sign in again", async ({ page }) => {
  const email = await registerUser(page, "Grace Hopper");
  await expect(page.getByText(/Good (morning|afternoon|evening), Grace/)).toBeVisible();
  await page.goto("/profile");
  await page.getByRole("main").getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("wrong-pass1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert").filter({ hasText: /\w/ }).first()).toContainText("Incorrect email or password");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
});

test("registration validates input client-side", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Email").fill("not-an-email");
  await page.getByLabel("Password", { exact: true }).fill("short");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Enter a valid email address.")).toBeVisible();
  await expect(page.getByText("Password must be at least 8 characters.")).toBeVisible();
  await expect(page).toHaveURL(/\/register/);
});
