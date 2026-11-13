import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

type FilePayload = { name: string; mimeType: string; buffer: Buffer };

const phone = process.env.E2E_AUTH_PHONE;
const otp = process.env.E2E_AUTH_OTP;
const validationRoot = process.env.E2E_GROUNDNUT_VALIDATION_ROOT
  ?? "C:/AGRONEX/datasets/groundnut_clean_split/validation/early_leaf_spot";

const samples = {
  high: path.join(validationRoot, "IMG_0371.JPG"),
  medium: path.join(validationRoot, "IMG_0325.JPG"),
  low: path.join(validationRoot, "IMG_0874.JPG"),
};
const darkImage: FilePayload = {
  name: "dark-groundnut.png",
  mimeType: "image/png",
  buffer: Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAASAAAAEgCAIAAACb4TnXAAABCUlEQVR4nO3BMQEAAADCoPVPbQ0PoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADo0ADNTQAB0Py5WAAAAABJRU5ErkJggg==",
    "base64",
  ),
};

async function signInThroughUi(page: Page) {
  if (!phone || !otp) throw new Error("E2E_AUTH_PHONE and E2E_AUTH_OTP are required");
  await page.goto("/(auth)/login");
  await page.getByTestId("phone-number-input").fill(phone);
  await page.getByRole("button", { name: /send otp/i }).click();
  await page.getByTestId("otp-native-input").fill(otp);
  await page.getByRole("button", { name: /^verify$/i }).click();
  await expect(page).not.toHaveURL(/\/(auth)\/(login|otp)|\/login|\/otp/);
}

async function chooseFile(page: Page, filename: string | FilePayload) {
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: /choose from gallery/i }).click();
  await (await chooser).setFiles(filename);
}

async function enterGroundnutDoctor(page: Page, filename: string) {
  await page.goto("/disease");
  await chooseFile(page, filename);
  const groundnut = page.getByRole("radio", { name: /groundnut/i }).or(
    page.getByRole("button", { name: /groundnut/i }),
  );
  await expect(groundnut.first()).toBeVisible();
  await groundnut.first().click();
  await page.getByRole("button", { name: /confirm/i }).click();
  await expect(page.getByText("Groundnut Crop Doctor")).toBeVisible();
}

async function analyze(page: Page) {
  await expect(page.getByLabel("Selected Groundnut leaf photograph")).toBeVisible();
  const request = page.waitForResponse((response) =>
    response.url().includes("/api/v1/doctor/groundnut/predict")
      && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Analyze Groundnut leaf" }).click();
  await expect(page.getByRole("progressbar")).toBeVisible();
  expect((await request).status()).toBe(200);
  await expect(page.getByTestId("groundnut-result")).toBeVisible();
}

test("unauthenticated users cannot open the Groundnut doctor", async ({ page }, testInfo) => {
  await page.goto("/disease");
  await expect(page).not.toHaveURL(/\/disease(?:$|\?)/);
  await expect(page.getByText("Groundnut Crop Doctor")).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("unauthorized-entry-boundary.png"), fullPage: true });
});

test.describe("authorized Groundnut visual acceptance", () => {
  test.skip(!phone || !otp, "Requires a real authorized test account via E2E_AUTH_PHONE/E2E_AUTH_OTP");

  test.beforeEach(async ({ page }) => signInThroughUi(page));

  for (const [category, filename] of Object.entries(samples)) {
    test(`${category.toUpperCase()} prediction renders complete safety information`, async ({ page }, testInfo) => {
      await enterGroundnutDoctor(page, filename);
      await analyze(page);
      await expect(page.getByText(/Experimental model/i)).toBeVisible();
      await expect(page.getByText(/70\.22%/)).toBeVisible();
      await expect(page.getByText(/Top three model candidates/i)).toBeVisible();
      await expect(page.getByText(/Image quality/i)).toBeVisible();
      await expect(page.getByText(new RegExp(category, "i"))).toBeVisible();
      if (category !== "high") await expect(page.getByText(/Expert review required/i)).toBeVisible();
      await page.screenshot({ path: testInfo.outputPath(`${category}-result.png`), fullPage: true });
    });
  }

  test("REJECTED quality result does not present a diagnosis", async ({ page }, testInfo) => {
    await enterGroundnutDoctor(page, samples.high);
    await page.getByRole("button", { name: /replace image/i }).click();
    await chooseFile(page, darkImage);
    await analyze(page);
    await expect(page.getByText("Photograph not accepted")).toBeVisible();
    await expect(page.getByText("Rejected", { exact: true })).toBeVisible();
    await expect(page.getByText("Likely classification")).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath("rejected-result.png"), fullPage: true });
  });

  test("replaces a rejected image and retries", async ({ page }, testInfo) => {
    await enterGroundnutDoctor(page, samples.high);
    await page.getByRole("button", { name: /replace image/i }).click();
    await expect(page.getByRole("button", { name: /choose from gallery/i })).toBeVisible();
    await chooseFile(page, samples.high);
    await analyze(page);
    await expect(page.getByRole("button", { name: /analyze another photograph/i })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("replace-and-retry.png"), fullPage: true });
  });
});
