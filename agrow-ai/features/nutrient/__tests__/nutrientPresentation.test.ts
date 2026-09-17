import {
  mayDisplayNutrientFinding,
  safeDisplayStatus,
} from "../services/nutrientPresentation";

describe("nutrient presentation safety", () => {
  it.each([
    "abstained",
    "invalid_image",
    "crop_mismatch",
    "unsupported_crop",
    "provider_unavailable",
  ])("hides provider nutrient labels for %s", (code) => {
    expect(mayDisplayNutrientFinding(code as never)).toBe(false);
    expect(safeDisplayStatus(code as never, "possible")).toBe("not_confirmed");
  });

  it.each(["supported_finding", "possible_finding"])(
    "shows a safety-approved %s",
    (code) => {
      expect(mayDisplayNutrientFinding(code as never)).toBe(true);
    },
  );
});
