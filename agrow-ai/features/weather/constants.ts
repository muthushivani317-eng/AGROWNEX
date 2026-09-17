import type {
  InsightCategory,
  InsightSeverity,
  WeatherCondition,
} from "./types";

/** Refresh cadence (docs: background refresh; backend caches for 5 min). */
export const WEATHER_STALE_MS = 1000 * 60 * 5;
export const WEATHER_REFRESH_MS = 1000 * 60 * 15;

/** MMKV keys. */
export const WEATHER_CACHE_PREFIX = "agrowai.weather.bundle.";
export const SELECTED_FARM_KEY = "agrowai.weather.selectedFarm";

export const weatherKeys = {
  all: ["weather"] as const,
  farm: (id: string) => ["weather", "farm", id] as const,
};

/** Condition → i18n label key (under the `weather` namespace). */
export const CONDITION_LABEL_KEY: Record<WeatherCondition, string> = {
  clear: "weather.conditionClear",
  partly_cloudy: "weather.conditionPartlyCloudy",
  cloudy: "weather.conditionCloudy",
  fog: "weather.conditionFog",
  drizzle: "weather.conditionDrizzle",
  rain: "weather.conditionRain",
  snow: "weather.conditionSnow",
  thunderstorm: "weather.conditionThunderstorm",
};

/** Insight category → i18n label key. */
export const CATEGORY_LABEL_KEY: Record<InsightCategory, string> = {
  irrigation: "weather.categoryIrrigation",
  spraying: "weather.categorySpraying",
  heat_stress: "weather.categoryHeatStress",
  heavy_rain: "weather.categoryHeavyRain",
  wind: "weather.categoryWind",
  field_work: "weather.categoryFieldWork",
};

/** Backend insight code → localized message key (params interpolated). */
export const INSIGHT_MESSAGE_KEY: Record<string, string> = {
  "heat_stress.high": "weather.msgHeatHigh",
  "heat_stress.extreme": "weather.msgHeatExtreme",
  "heavy_rain.expected": "weather.msgRainExpected",
  "heavy_rain.severe": "weather.msgRainSevere",
  "wind.high": "weather.msgWindHigh",
  "wind.strong": "weather.msgWindStrong",
  "spraying.good_window": "weather.msgSprayGood",
  "spraying.avoid_wind": "weather.msgSprayAvoidWind",
  "spraying.avoid_rain": "weather.msgSprayAvoidRain",
  "irrigation.hold": "weather.msgIrrigationHold",
  "irrigation.recommended": "weather.msgIrrigationRecommended",
  "irrigation.normal": "weather.msgIrrigationNormal",
  "field_work.favorable": "weather.msgFieldFavorable",
  "field_work.unfavorable": "weather.msgFieldUnfavorable",
};

/** Ranked mission code -> localized action and optional avoid-copy keys. */
export const MISSION_ACTION_KEY: Record<string, string> = {
  "heavy_rain.severe": "weather.missionActionRainSevere",
  "heavy_rain.expected": "weather.missionActionRainExpected",
  "heat_stress.extreme": "weather.missionActionHeatExtreme",
  "heat_stress.high": "weather.missionActionHeatHigh",
  "wind.strong": "weather.missionActionWindStrong",
  "wind.high": "weather.missionActionWindHigh",
  "spraying.avoid_rain": "weather.missionActionSprayRain",
  "spraying.avoid_wind": "weather.missionActionSprayWind",
  "irrigation.hold": "weather.missionActionIrrigationHold",
  "irrigation.recommended": "weather.missionActionIrrigationRecommended",
  "field_work.unfavorable": "weather.missionActionFieldUnfavorable",
  "field_work.favorable": "weather.missionActionFieldFavorable",
  "spraying.good_window": "weather.missionActionSprayGood",
  "irrigation.normal": "weather.missionActionIrrigationNormal",
};

export const MISSION_AVOID_KEY: Record<string, string> = {
  "heavy_rain.severe": "weather.missionAvoidRainSevere",
  "heavy_rain.expected": "weather.missionAvoidRainExpected",
  "heat_stress.extreme": "weather.missionAvoidHeatExtreme",
  "heat_stress.high": "weather.missionAvoidHeatHigh",
  "wind.strong": "weather.missionAvoidWind",
  "wind.high": "weather.missionAvoidWind",
  "spraying.avoid_rain": "weather.missionAvoidSprayRain",
  "spraying.avoid_wind": "weather.missionAvoidWind",
  "irrigation.hold": "weather.missionAvoidIrrigation",
  "field_work.unfavorable": "weather.missionAvoidFieldWork",
};

/** Severity → AgBadge tone. */
export const SEVERITY_TONE: Record<
  InsightSeverity,
  "neutral" | "info" | "warning" | "danger"
> = {
  info: "neutral",
  advice: "info",
  warning: "warning",
  critical: "danger",
};
