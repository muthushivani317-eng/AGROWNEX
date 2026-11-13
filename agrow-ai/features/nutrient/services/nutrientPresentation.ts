import type { DeficiencyStatus, NutrientResultCode } from "../types";

type ConfidenceBand = "low" | "medium" | "high" | null;

export function mayDisplayNutrientFinding(code: NutrientResultCode): boolean {
  return code === "supported_finding" || code === "possible_finding";
}

export function safeDisplayStatus(
  code: NutrientResultCode,
  status: DeficiencyStatus,
): DeficiencyStatus {
  return mayDisplayNutrientFinding(code) ? status : "not_confirmed";
}

export function mayDisplayNutrientConfidence(
  confidence: number | null,
  band: ConfidenceBand,
): boolean {
  return confidence !== null && band !== null;
}
