import type { DrainageClass, Severity, SoilSource } from "./types";

export const SOIL_DASHBOARD_CACHE_KEY = "agrowai.soil.dashboard.cache";
export const SOIL_HISTORY_CACHE_KEY = "agrowai.soil.history.cache";
export const SOIL_LOCAL_KEY = "agrowai.soil.local";
export const SOIL_OUTBOX_KEY = "agrowai.soil.outbox";
export const SOIL_SCAN_CACHE_KEY = "agrowai.soil.scan.cache.v1";
export const SOIL_SCAN_HISTORY_CACHE_KEY = "agrowai.soil.scan.history.cache.v1";

export const DEFAULT_PAGE_SIZE = 20;

export const soilKeys = {
  all: ["soil"] as const,
  dashboard: (farmId: string) => ["soil", "dashboard", farmId] as const,
  history: (farmId: string) => ["soil", "history", farmId] as const,
  recommendations: (farmId: string) =>
    ["soil", "recommendations", farmId] as const,
  latest: (farmId: string) => ["soil", "latest", farmId] as const,
};

/** The soil parameters shown on the Soil Health Card, in display order. */
export const CARD_PARAMETERS = [
  "ph",
  "organic_carbon",
  "nitrogen",
  "phosphorus",
  "potassium",
  "ec_salinity",
] as const;

export const PARAMETER_LABEL_KEY: Record<string, string> = {
  ph: "soil.paramPh",
  organic_carbon: "soil.paramOrganicCarbon",
  nitrogen: "soil.paramNitrogen",
  phosphorus: "soil.paramPhosphorus",
  potassium: "soil.paramPotassium",
  ec_salinity: "soil.paramSalinity",
  water_holding_capacity: "soil.paramWaterHolding",
  drainage: "soil.paramDrainage",
  soil_type: "soil.paramSoilType",
};

export const RATING_LABEL_KEY: Record<string, string> = {
  low: "soil.ratingLow",
  medium: "soil.ratingMedium",
  high: "soil.ratingHigh",
  optimal: "soil.ratingOptimal",
  unknown: "soil.ratingUnknown",
  strongly_acidic: "soil.phStronglyAcidic",
  acidic: "soil.phAcidic",
  neutral: "soil.phNeutral",
  alkaline: "soil.phAlkaline",
  strongly_alkaline: "soil.phStronglyAlkaline",
};

/** Tone for a rating chip. Low/deficient reads as caution, optimal as success. */
export const RATING_TONE: Record<
  string,
  "success" | "warning" | "danger" | "info" | "neutral"
> = {
  low: "warning",
  medium: "info",
  high: "success",
  optimal: "success",
  unknown: "neutral",
  strongly_acidic: "danger",
  acidic: "warning",
  neutral: "success",
  alkaline: "warning",
  strongly_alkaline: "danger",
};

export const SEVERITY_TONE: Record<
  Severity,
  "info" | "success" | "warning" | "danger"
> = {
  info: "success",
  advice: "info",
  warning: "warning",
  critical: "danger",
};

export const SOURCE_LABEL_KEY: Record<SoilSource, string> = {
  self: "soil.sourceSelf",
  soil_health_card: "soil.sourceShc",
  lab: "soil.sourceLab",
  government: "soil.sourceGovernment",
  satellite: "soil.sourceSatellite",
  farm_registration: "soil.sourceFarm",
  estimate: "soil.sourceEstimate",
};

export const SOURCES: SoilSource[] = ["self", "soil_health_card", "lab"];

export const DRAINAGE_OPTIONS: DrainageClass[] = [
  "poor",
  "moderate",
  "good",
  "excessive",
];

export const DRAINAGE_LABEL_KEY: Record<DrainageClass, string> = {
  poor: "soil.drainagePoor",
  moderate: "soil.drainageModerate",
  good: "soil.drainageGood",
  excessive: "soil.drainageExcessive",
};
