import { en } from "@/localization/locales/en";

export type DiseaseRiskOutcome =
  | "RULE_PACK_UNAVAILABLE"
  | "INSUFFICIENT_DATA"
  | "STAGE_UNCONFIRMED"
  | "OUT_OF_SCOPE"
  | "CONDITIONS_NOT_MET"
  | "RISK_CONDITIONS_PRESENT";

export interface DiseaseRiskEvaluation {
  outcome: DiseaseRiskOutcome;
  cropId: string;
  confirmedStage: string | null;
  forecastPeriod: string | null;
  weatherCauseKeys: string[];
  weatherSource: "live" | "cached" | "stale" | "missing";
  ruleSource: string | null;
  missingFields: string[];
}

export interface ApiDiseaseRiskEvaluation {
  outcome: DiseaseRiskOutcome;
  crop_id: string;
  confirmed_stage: string | null;
  forecast_period: string | null;
  weather_cause_keys: string[];
  weather_source: "live" | "cached" | "stale" | "missing";
  rule_source: string | null;
  missing_fields: string[];
}

export interface DiseaseRiskAlert {
  id: string;
  farmId: string;
  crop: string;
  diseaseKey: string | null;
  status: string;
  riskLevel: string | null;
  confidence: string;
  weatherFactors: string[];
  weatherSource: string;
  cropStage: string | null;
  generatedAt: string;
  validUntil: string | null;
  ruleVersion: string | null;
  ruleVerificationStatus: string;
  farmerMessageKey: string;
  missingInputs: string[];
  acknowledgedAt: string | null;
  cached: boolean;
}

export interface ApiDiseaseRiskAlert {
  id: string;
  farm_id: string;
  crop: string;
  disease_key: string | null;
  status: string;
  risk_level: string | null;
  confidence: string;
  weather_factors: string[];
  weather_source: string;
  crop_stage: string | null;
  generated_at: string;
  valid_until: string | null;
  rule_version: string | null;
  rule_verification_status: string;
  farmer_message_key: string;
  missing_inputs: string[];
  acknowledged_at: string | null;
  cached: boolean;
}

/**
 * The exact, closed set of `farmer_message_key` values the backend ever emits
 * (backend/app/modules/disease_risk/service.py -- the `message` local there).
 * Kept here as the single source of truth so a translation-coverage test can
 * assert every key has a real copy in every locale, and so farmerMessageOrFallback
 * below never has to guess.
 */
export const KNOWN_FARMER_MESSAGE_KEYS = [
  "diseaseRisk.noVerifiedRule",
  "diseaseRisk.conditionsPresent",
  "diseaseRisk.insufficientData",
] as const;

/**
 * Resolve a disease-risk `farmer_message_key` to real, farmer-facing copy --
 * never the raw i18n key itself. react-i18next's default behaviour when a key
 * has no translation is to echo the key back unchanged; without this guard a
 * farmer could see a literal string like "diseaseRisk.someFutureKey" instead
 * of guidance (2026-08 pre-release audit -- same class of bug as the raw-slug
 * leak fixed in SchemeDetailScreen). Falls back to the safe, always-present
 * "no verified rule" copy rather than a translated string, since translating
 * again would just echo the same unknown key back.
 */
export function farmerMessageOrFallback(
  key: string,
  translate: (key: string, options?: Record<string, unknown>) => string,
): string {
  const translated = translate(key);
  return translated === key ? en.diseaseRisk.noVerifiedRule : translated;
}
