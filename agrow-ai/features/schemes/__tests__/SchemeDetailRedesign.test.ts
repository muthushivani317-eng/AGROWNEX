import fs from "node:fs";
import path from "node:path";
import { splitSchemeBenefits } from "../utils/splitSchemeBenefits";
import { en } from "../../../localization/locales/en";
import { ta } from "../../../localization/locales/ta";

test("benefit grouping preserves currency amounts and conditions without inventing data", () => {
  const text =
    "For members: pension (₹1,000/month), accident relief (₹20,000–₹1,00,000 depending on severity), funeral support (₹2,500).";
  expect(splitSchemeBenefits(text)).toEqual([
    "For members: pension (₹1,000/month)",
    "accident relief (₹20,000–₹1,00,000 depending on severity)",
    "funeral support (₹2,500).",
  ]);
  expect(
    splitSchemeBenefits("Relief ₹1,00,000, subject to verification"),
  ).toEqual(["Relief ₹1,00,000", "subject to verification"]);
  expect(
    splitSchemeBenefits(
      "ஓய்வூதியம் (₹1,000/மாதம்), இறுதிச் சடங்கு உதவி (₹2,500)",
    ),
  ).toHaveLength(2);
});

test("detail redesign retains live data, bookmark, refresh, documents and official actions", () => {
  const source = fs.readFileSync(
    path.resolve(__dirname, "../screens/SchemeDetailScreen.tsx"),
    "utf8",
  );
  for (const expected of [
    "scheme.title",
    "scheme.description",
    "scheme.eligibility",
    "scheme.documents.map",
    "scheme.applicationSteps.map",
    "scheme.departments.join",
    "toggleBookmark",
    "RefreshControl",
    "openBrowserAsync(scheme.officialUrl)",
    'accessibilityRole="progressbar"',
    "styles.benefitGrid",
    "styles.hero",
  ])
    expect(source).toContain(expected);
  expect(source).not.toContain("useAppTheme");
  expect(source).not.toContain("59%");
  expect(source).not.toContain("₹1,000");
  for (const key of [
    "fullEligibility",
    "eligibilityContext",
    "amountCaution",
    "viewOfficialSource",
  ] as const) {
    expect(en.schemes[key]).toBeTruthy();
    expect(ta.schemes[key]).toMatch(/[\u0B80-\u0BFF]/);
  }
});
