import { nutrientErrorMessageKey } from "../services/nutrientErrorMessage";

describe("nutrientErrorMessageKey", () => {
  it.each([
    ["analysis_unavailable", "nutrient.providerUnavailable"],
    ["storage_provider_unavailable", "nutrient.storageUnavailable"],
    ["nutrient_analysis_failed", "nutrient.providerFailure"],
    ["nutrient_crop_mismatch", "nutrient.cropMismatch"],
    ["nutrient_unsupported_crop", "nutrient.unsupportedCrop"],
    ["poor_image_quality", "nutrient.poorQuality"],
    ["no_plant_detected", "nutrient.noPlant"],
    ["ai_daily_quota_exceeded", "nutrient.quotaExceeded"],
    // A timeout is not the same claim as "you're offline" -- both collapse
    // to ApiError status 0, but the client tags them apart (2026-09-03
    // regression: analysis can legitimately take 15-38s).
    ["timeout_error", "nutrient.timedOut"],
    ["network_error", "nutrient.offline"],
  ])("maps %s to an actionable farmer message", (code, expected) => {
    expect(nutrientErrorMessageKey(code)).toBe(expected);
  });

  it("uses the safe generic message for unknown or missing codes", () => {
    expect(nutrientErrorMessageKey("unexpected")).toBe("nutrient.genericError");
    expect(nutrientErrorMessageKey(undefined)).toBe("nutrient.genericError");
  });
});
