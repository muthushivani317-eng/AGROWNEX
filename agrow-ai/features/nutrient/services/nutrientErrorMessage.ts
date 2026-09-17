const NUTRIENT_ERROR_KEYS: Readonly<Record<string, string>> = {
  ai_daily_quota_exceeded: "nutrient.quotaExceeded",
  poor_image_quality: "nutrient.poorQuality",
  no_plant_detected: "nutrient.noPlant",
  analysis_unavailable: "nutrient.providerUnavailable",
  storage_provider_unavailable: "nutrient.storageUnavailable",
  nutrient_analysis_failed: "nutrient.providerFailure",
  nutrient_crop_mismatch: "nutrient.cropMismatch",
  nutrient_unsupported_crop: "nutrient.unsupportedCrop",
  // A client-side timeout and a genuine offline device both collapse to
  // ApiError status 0, but the client tags the underlying axios error code
  // separately (services/apiClient.ts) so they don't have to share one
  // message here (2026-09-03: analysis can legitimately take 15-38s).
  timeout_error: "nutrient.timedOut",
  network_error: "nutrient.offline",
};

export function nutrientErrorMessageKey(code: string | undefined): string {
  return (code && NUTRIENT_ERROR_KEYS[code]) || "nutrient.genericError";
}

type Translate = (key: string, options?: Record<string, unknown>) => string;

function titleCase(value: string): string {
  return value
    .split(" ")
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

/** Localized display label for a normalized crop id (e.g. "pearl millet"),
 * falling back to a title-cased version of the raw value for a crop that
 * isn't in the nutrient.cropNames table -- the backend's crop normalization
 * isn't limited to a fixed list (app/modules/nutrient/crops.py), so this
 * table can never be guaranteed complete. */
function cropLabel(t: Translate, crop: string): string {
  const key = crop.trim().toLowerCase().replace(/\s+/g, "_");
  return t(`nutrient.cropNames.${key}`, { defaultValue: titleCase(crop) });
}

/**
 * A `nutrient_crop_mismatch` error's full, specific message -- naming both
 * the farm's registered crop and the crop the photo actually showed -- when
 * the backend supplied that detail (details.expected_crop /
 * details.observed_crop). Returns null when it can't be built (an older
 * backend response, or a locally-queued offline error with no details), so
 * the caller can fall back to the generic "doesn't match" copy.
 */
export function nutrientCropMismatchMessage(
  t: Translate,
  details: Record<string, string> | undefined,
): string | null {
  const expected = details?.expected_crop;
  const observed = details?.observed_crop;
  if (!expected || !observed) return null;
  return t("nutrient.cropMismatchDetailed", {
    expected: cropLabel(t, expected),
    observed: cropLabel(t, observed),
  });
}
