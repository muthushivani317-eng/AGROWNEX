/**
 * Indicators that cannot produce a measured result without a submitted soil
 * laboratory report. Mapped estimates have separate indicator codes and must
 * not be presented as laboratory measurements.
 */
const LAB_REPORT_REQUIRED_INDICATORS = new Set([
  "salinity_risk",
  "organic_matter_trend",
  "acidity_ph_risk",
]);

export type IndicatorAvailabilityLabel =
  | "available"
  | "lab_report_required"
  | "insufficient";

export function getIndicatorAvailabilityLabel(
  code: string,
  status: string,
): IndicatorAvailabilityLabel {
  if (status === "available") return "available";
  if (LAB_REPORT_REQUIRED_INDICATORS.has(code)) {
    return "lab_report_required";
  }
  return "insufficient";
}
