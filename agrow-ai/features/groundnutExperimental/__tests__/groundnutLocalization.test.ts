import { en } from "@/localization/locales/en";
import { ml } from "@/localization/locales/ml";
import { ta } from "@/localization/locales/ta";

const expectedClasses = [
  "early_leaf_spot",
  "healthy_leaf",
  "late_leaf_spot",
  "nutrition_deficiency",
  "rust",
];
const expectedApiErrors = [
  "authentication",
  "authorization",
  "too_large",
  "unsupported_type",
  "invalid_input",
  "unavailable",
  "unknown",
] as const;

test.each([en.groundnut, ta.groundnut, ml.groundnut])(
  "Groundnut locale includes complete experimental safety and class copy",
  (copy) => {
    expect(copy.title).toBeTruthy();
    expect(copy.camera).toBeTruthy();
    expect(copy.gallery).toBeTruthy();
    expect(copy.experimentalBody).toContain("70.22%");
    expect(copy.expertReviewBody).toBeTruthy();
    for (const code of expectedApiErrors) {
      expect(copy.symptoms.apiErrors[code]).toBeTruthy();
      expect(copy.voice.apiErrors[code]).toBeTruthy();
    }
    expect(Object.keys(copy.diseases)).toEqual(expectedClasses);
    for (const disease of Object.values(copy.diseases)) {
      expect(disease.name).toBeTruthy();
      expect(disease.description).toBeTruthy();
    }
  },
);
