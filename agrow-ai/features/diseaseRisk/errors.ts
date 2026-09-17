import { ApiError } from "@/types";

export type DiseaseRiskErrorMessageKey =
  | "diseaseRisk.errors.network"
  | "diseaseRisk.errors.authentication"
  | "diseaseRisk.errors.farmAccess"
  | "diseaseRisk.errors.unavailable"
  | "diseaseRisk.errors.validation"
  | "diseaseRisk.errors.server";

const UNAVAILABLE_CODES = new Set([
  "RULE_REGISTRY_UNAVAILABLE",
  "DISEASE_RISK_UNAVAILABLE",
  "SERVICE_UNAVAILABLE",
]);

/** Resolve a reviewed message without exposing raw server details. */
export function diseaseRiskErrorMessageKey(
  error: unknown,
): DiseaseRiskErrorMessageKey {
  if (!(error instanceof ApiError)) return "diseaseRisk.errors.server";
  if (error.isNetwork) return "diseaseRisk.errors.network";
  if (error.isAuth) return "diseaseRisk.errors.authentication";
  if (error.errorCode === "FARM_NOT_OWNED") {
    return "diseaseRisk.errors.farmAccess";
  }
  if (error.status === 422) return "diseaseRisk.errors.validation";
  if (UNAVAILABLE_CODES.has(error.errorCode) || error.status === 503) {
    return "diseaseRisk.errors.unavailable";
  }
  return "diseaseRisk.errors.server";
}
