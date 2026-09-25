import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { analyzeManually, registerUser } from "./helpers";

async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

async function axe(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  return results.violations.map((v) => `${label} ${v.id}: ${v.nodes.map((n) => n.target).join(" | ")}`);
}

test("public pages are responsive and accessible", async ({ page }) => {
  for (const url of ["/", "/features", "/how-it-works", "/login", "/register", "/privacy", "/terms"]) {
    await page.goto(url);
    await noHorizontalScroll(page);
    expect(await axe(page, url)).toEqual([]);
  }
});

test("app navigation adapts to the viewport", async ({ page }) => {
  await registerUser(page);
  const width = page.viewportSize()!.width;
  const bottomNav = page.getByRole("navigation", { name: "Primary" });
  const sidebar = page.getByRole("navigation", { name: "Main" });
  if (width < 1024) {
    await expect(bottomNav).toBeVisible();
    await expect(sidebar).toBeHidden();
    const scan = bottomNav.getByRole("link", { name: "Scan" });
    const box = await scan.boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(44); // touch-friendly target
    for (const name of ["Home", "History", "Saved", "Profile"]) {
      const b = await bottomNav.getByRole("link", { name }).boundingBox();
      expect(b!.height).toBeGreaterThanOrEqual(44);
    }
    await scan.click();
  } else {
    await expect(sidebar).toBeVisible();
    await expect(bottomNav).toBeHidden();
    await page.getByRole("link", { name: "Scan product" }).first().click();
  }
  await expect(page).toHaveURL(/\/scan/);
  await noHorizontalScroll(page);
});

test("app pages have no horizontal overflow and pass axe", async ({ page }) => {
  await registerUser(page);
  await analyzeManually(page, "Axe Bar", "oats, sugar, soy lecithin, red 40");
  const resultUrl = new URL(page.url()).pathname;
  await page.getByRole("button", { name: "Save product" }).click();
  const violations: string[] = [];
  for (const url of ["/dashboard", "/scan", "/analyze", resultUrl, "/history", "/saved", "/compare", "/profile", "/settings"]) {
    await page.goto(url);
    await page.waitForLoadState("networkidle");
    await noHorizontalScroll(page);
    violations.push(...(await axe(page, url)));
  }
  expect(violations).toEqual([]);
});

test("keyboard users can skip to content", async ({ page }) => {
  await registerUser(page);
  await page.goto("/analyze");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main/);
});

test("dark mode result page is accessible", async ({ browser }) => {
  const ctx = await browser.newContext({ colorScheme: "dark", baseURL: "http://localhost:3000" });
  const page = await ctx.newPage();
  await registerUser(page);
  await analyzeManually(page, "Dark Bar", "almonds, dates, cocoa, sugar, red 40");
  await expect(page.locator("html")).toHaveClass(/dark/);
  expect(await axe(page, "dark result")).toEqual([]);
  await ctx.close();
});
