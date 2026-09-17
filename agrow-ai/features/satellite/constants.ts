import type {
  IndexName,
  MoistureStatus,
  Severity,
  StressLevel,
  VegetationHealth,
} from "./types";

export const SAT_DASHBOARD_CACHE_KEY = "agrowai.satellite.dashboard.cache";
export const SAT_HISTORY_CACHE_KEY = "agrowai.satellite.history.cache";
export const SAT_TIMELINE_CACHE_KEY = "agrowai.satellite.timeline.cache";
export const SAT_WATERLOGGING_CACHE_KEY =
  "agrowai.satellite.waterlogging.cache";
export const SAT_WATERLOGGING_HISTORY_CACHE_KEY =
  "agrowai.satellite.waterlogging.history.cache";
export const SAT_LOCAL_KEY = "agrowai.satellite.local";
export const SAT_OUTBOX_KEY = "agrowai.satellite.outbox";

export const DEFAULT_PAGE_SIZE = 20;

export const satelliteKeys = {
  all: ["satellite"] as const,
  dashboard: (farmId: string) => ["satellite", "dashboard", farmId] as const,
  history: (farmId: string) => ["satellite", "history", farmId] as const,
  timeline: (farmId: string, range: string) =>
    ["satellite", "timeline", farmId, range] as const,
  alerts: (farmId: string) => ["satellite", "alerts", farmId] as const,
  waterlogging: (farmId: string) =>
    ["satellite", "waterlogging", farmId] as const,
  waterloggingHistory: (farmId: string) =>
    ["satellite", "waterlogging", "history", farmId] as const,
};

export const INDEX_ORDER: IndexName[] = ["ndvi", "ndre", "evi", "ndmi"];

export const INDEX_LABEL_KEY: Record<string, string> = {
  ndvi: "satellite.indexNdvi",
  ndre: "satellite.indexNdre",
  evi: "satellite.indexEvi",
  ndmi: "satellite.indexNdmi",
};

export const HEALTH_LABEL_KEY: Record<VegetationHealth, string> = {
  bare: "satellite.healthBare",
  very_low: "satellite.healthVeryLow",
  low: "satellite.healthLow",
  moderate: "satellite.healthModerate",
  good: "satellite.healthGood",
  very_good: "satellite.healthVeryGood",
  unknown: "satellite.healthUnknown",
};

export const HEALTH_TONE: Record<
  VegetationHealth,
  "success" | "warning" | "danger" | "neutral"
> = {
  bare: "danger",
  very_low: "danger",
  low: "warning",
  moderate: "warning",
  good: "success",
  very_good: "success",
  unknown: "neutral",
};

export const STRESS_LABEL_KEY: Record<StressLevel, string> = {
  none: "satellite.stressNone",
  mild: "satellite.stressMild",
  moderate: "satellite.stressModerate",
  severe: "satellite.stressSevere",
  unknown: "satellite.stressUnknown",
};

export const STRESS_TONE: Record<
  StressLevel,
  "success" | "warning" | "danger" | "neutral"
> = {
  none: "success",
  mild: "warning",
  moderate: "warning",
  severe: "danger",
  unknown: "neutral",
};

export const MOISTURE_LABEL_KEY: Record<MoistureStatus, string> = {
  very_dry: "satellite.moistureVeryDry",
  dry: "satellite.moistureDry",
  adequate: "satellite.moistureAdequate",
  moist: "satellite.moistureMoist",
  wet: "satellite.moistureWet",
  unknown: "satellite.moistureUnknown",
};

export const MOISTURE_TONE: Record<
  MoistureStatus,
  "success" | "warning" | "danger" | "info" | "neutral"
> = {
  very_dry: "danger",
  dry: "warning",
  adequate: "success",
  moist: "info",
  wet: "info",
  unknown: "neutral",
};

export const TREND_LABEL_KEY: Record<string, string> = {
  improving: "satellite.trendImproving",
  stable: "satellite.trendStable",
  declining: "satellite.trendDeclining",
  unknown: "satellite.trendUnknown",
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

export const TIMELINE_WEEKLY = "weekly";
export const TIMELINE_MONTHLY = "monthly";
