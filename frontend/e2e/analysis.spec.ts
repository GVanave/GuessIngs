import path from "node:path";
import { expect, test } from "@playwright/test";
import { analyzeManually, registerUser } from "./helpers";

test.beforeEach(async ({ page }) => {
  await registerUser(page);
});

test("manual analysis shows score, verdict, breakdown and all sections", async ({ page }) => {
  await analyzeManually(
    page,
    "Choco Oat Bar",
    "Whole Grain Oats, Sugar, Chocolate Chips (Sugar, Cocoa Butter, Soy Lecithin), Salt, Natural Flavor",
  );
  // 100 − 25 (sugar 2nd) − 5 (soy lecithin) − 20 (NOVA 4) + 5 (oats) = 55
  await expect(page.getByRole("img", { name: /Score 55 out of 100\. Verdict YELLOW/ })).toBeVisible();
  await expect(page.getByTestId("final-score")).toHaveText("55");
  for (const heading of ["Why this score?", "Positive ingredients", "Ingredients to watch", "Score breakdown", "Full ingredients", "Better alternatives"]) {
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(page.getByTestId("line-added_sugar")).toContainText("−25");
  await expect(page.getByTestId("line-nova4")).toContainText("−20");
  await expect(page.getByText("Duplicate — counted once")).toBeVisible();

  await page.getByRole("button", { name: "Verify score" }).click();
  await expect(page.getByText(/Reproducible: recomputed score 55 matches/)).toBeVisible();
});

test("same ingredients always give the same score", async ({ page }) => {
  const list = "sugar, wheat flour, palm oil, cocoa, soy lecithin, vanillin";
  await analyzeManually(page, "Cookies A", list);
  const first = await page.getByTestId("final-score").textContent();
  await analyzeManually(page, "Cookies B", list.toUpperCase());
  await expect(page.getByTestId("final-score")).toHaveText(first!);
});

test("empty input and unknown ingredients are handled clearly", async ({ page }) => {
  await page.goto("/analyze");
  await page.getByRole("button", { name: "Analyze ingredients" }).click();
  await expect(page.getByText("Enter the ingredient list.")).toBeVisible();
  await page.getByLabel("Ingredients", { exact: true }).fill("zorblax, quintessa");
  await page.getByRole("button", { name: "Analyze ingredients" }).click();
  await expect(page).toHaveURL(/\/analysis\//);
  await expect(page.getByText(/weren't recognized/)).toBeVisible();
});

test("history, save, saved list and compare", async ({ page }) => {
  await analyzeManually(page, "Plain Muesli", "rolled oats, almonds, raisins");
  await analyzeManually(page, "Frosted Cereal", "sugar, corn flakes, red 40, bht");
  await page.getByRole("button", { name: "Save product" }).click();
  await expect(page.getByRole("button", { name: "Saved" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Plain Muesli/ })).toBeVisible(); // history-based alternative

  await page.goto("/saved");
  await expect(page.getByText("Frosted Cereal")).toBeVisible();

  await page.goto("/history");
  await expect(page.getByText("2 analyses")).toBeVisible();
  await page.getByRole("button", { name: "RED" }).click();
  await expect(page.getByText("1 analysis")).toBeVisible();
  await page.getByRole("button", { name: "All" }).click();
  await expect(page.getByText("2 analyses")).toBeVisible();
  await page.getByRole("button", { name: "Select to compare" }).click();
  await page.getByLabel("Select Plain Muesli").check();
  await page.getByLabel("Select Frosted Cereal").check();
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await expect(page).toHaveURL(/\/compare\?ids=/);
  await expect(page.getByText("Best pick")).toBeVisible();
  await expect(page.getByRole("table", { name: "Score contributions by rule" })).toBeVisible();
});

test("upload a label photo, review OCR text and analyze", async ({ page }) => {
  await page.goto("/scan");
  await page.getByTestId("file-input").setInputFiles(path.join(__dirname, "fixtures/label.png"));
  await expect(page.getByRole("heading", { name: "Review extracted ingredients" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByLabel("Ingredients", { exact: true })).toHaveValue(/oats/i);
  await page.getByLabel(/Product name/).fill("Scanned Oats");
  await page.getByRole("button", { name: "Analyze ingredients" }).click();
  await expect(page).toHaveURL(/\/analysis\//);
  await expect(page.getByText(/via upload/)).toBeVisible();
});

test("invalid and low-quality images show recovery actions", async ({ page }) => {
  await page.goto("/scan");
  await page.getByTestId("file-input").setInputFiles(path.join(__dirname, "fixtures/tiny.png"));
  await expect(page.getByRole("alert").filter({ hasText: /\w/ }).first()).toContainText("resolution is too low");
  await expect(page.getByRole("button", { name: "Retake photo" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Type instead" })).toBeVisible();

  await page.getByTestId("file-input").setInputFiles(path.join(__dirname, "fixtures/not-image.png"));
  await expect(page.getByRole("alert").filter({ hasText: /\w/ }).first()).toContainText("isn't a valid image");
});

test("delete an analysis", async ({ page }) => {
  await analyzeManually(page, "Delete Me", "water, sugar");
  await page.getByRole("button", { name: "Delete" }).first().click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
  await expect(page).toHaveURL(/\/history/);
  await expect(page.getByText("No analyses yet")).toBeVisible();
});

test("settings persist preferences", async ({ page }) => {
  await page.goto("/settings");
  const nova = page.getByRole("switch", { name: "Show NOVA processing group" });
  await expect(nova).toBeChecked();
  await nova.click();
  await expect(page.getByText("Settings saved.")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("switch", { name: "Show NOVA processing group" })).not.toBeChecked();
});
