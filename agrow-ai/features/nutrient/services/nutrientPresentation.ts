import type { DeficiencyStatus, NutrientResultCode } from "../types";

export function mayDisplayNutrientFinding(code: NutrientResultCode): boolean {
  return code === "supported_finding" || code === "possible_finding";
}

export function safeDisplayStatus(
  code: NutrientResultCode,
  status: DeficiencyStatus,
): DeficiencyStatus {
  return mayDisplayNutrientFinding(code) ? status : "not_confirmed";
}
