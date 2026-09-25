import { expect, type Page } from "@playwright/test";

export const PASSWORD = "Passw0rd!";

export function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

export async function registerUser(page: Page, name = "Test User") {
  const email = uniqueEmail();
  await page.goto("/register");
  await page.getByLabel("Name").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  return email;
}

export async function analyzeManually(page: Page, name: string, ingredients: string, sodium?: string) {
  await page.goto("/analyze");
  await page.getByLabel(/Product name/).fill(name);
  await page.getByLabel("Ingredients", { exact: true }).fill(ingredients);
  if (sodium) await page.getByLabel(/Sodium/).fill(sodium);
  await page.getByRole("button", { name: "Analyze ingredients" }).click();
  await expect(page).toHaveURL(/\/analysis\//);
  await expect(page.getByTestId("product-name")).toHaveText(name);
}
