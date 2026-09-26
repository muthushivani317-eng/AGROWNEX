import type {
  DeficiencyStatus,
  NutrientRecommendation,
  Severity,
} from "../types";

/**
 * Client-side mirror of the backend Nutrient Analysis Engine
 * (app/modules/nutrient/engine.py). Same transparent corroboration and confirm /
 * not-confirmed thresholds, so the local/offline provider reasons exactly like the
 * server. Never fabricates a deficiency — an inconclusive finding is ``not_confirmed``.
 */
const CONFIDENCE_CONFIRM = 75;
const CONFIDENCE_POSSIBLE = 50;
const CORROBORATION_BOOST = 12;
const STRONG_SOIL_BOOST = 18;
const CONTRADICTION_PENALTY = 15;
const DISEASE_CONFLICT_PENALTY = 20;
const CONFIDENCE_MIN = 0;
const CONFIDENCE_MAX = 99;

const MACRO = new Set(["nitrogen", "phosphorus", "potassium"]);
const SOIL_MICRO = new Set(["zinc", "iron", "manganese", "copper", "boron"]);

const REC_INFO = "info";
const REC_ADVICE = "advice";
const REC_WARNING = "warning";
const REC_CRITICAL = "critical";
const REC_ORDER: Record<string, number> = {
  info: 0,
  advice: 1,
  warning: 2,
  critical: 3,
};
const SEVERITY_TO_REC: Record<string, string> = {
  none: REC_INFO,
  mild: REC_ADVICE,
  moderate: REC_WARNING,
  severe: REC_CRITICAL,
  unknown: REC_ADVICE,
};

export interface Observation {
  primary: string | null;
  secondary: string | null;
  visualConfidence: number;
  severity: Severity;
  affectedArea: string | null;
}

export interface SoilRef {
  hasData: boolean;
  macroRatings: Record<string, string>; // nutrient → low|medium|high|unknown
  deficientMicronutrients: string[];
}
export interface SatelliteRef {
  hasData: boolean;
  vegetationHealth: string | null;
  lowVigor: boolean;
}
export interface WeatherRef {
  hasData: boolean;
  heavyRain: boolean;
}

export interface Assessment {
  primaryDeficiency: string | null;
  secondaryDeficiency: string | null;
  status: DeficiencyStatus;
  confidence: number;
  severity: Severity;
  affectedArea: string | null;
  soilSupports: boolean | null;
  satelliteSupports: boolean;
  weatherSupports: boolean;
  diseaseConflict: boolean;
  needsTest: boolean;
  needsExpert: boolean;
}

const clamp = (v: number): number =>
  Math.max(CONFIDENCE_MIN, Math.min(CONFIDENCE_MAX, v));

function soilSignal(primary: string, soil: SoilRef): [number, boolean | null] {
  if (!soil.hasData) return [0, null];
  if (MACRO.has(primary)) {
    const rating = soil.macroRatings[primary] ?? "unknown";
    if (rating === "low") return [STRONG_SOIL_BOOST, true];
    if (rating === "medium") return [CORROBORATION_BOOST, true];
    if (rating === "high") return [-CONTRADICTION_PENALTY, false];
    return [0, null];
  }
  if (SOIL_MICRO.has(primary)) {
    if (soil.deficientMicronutrients.includes(primary))
      return [STRONG_SOIL_BOOST, true];
    return [0, null];
  }
  return [0, null];
}

export interface CorroborateInput {
  soil?: SoilRef;
  satellite?: SatelliteRef;
  weather?: WeatherRef;
  diseaseConflict?: boolean;
}

export function corroborate(
  observation: Observation,
  { soil, satellite, weather, diseaseConflict = false }: CorroborateInput = {},
): Assessment {
  const s: SoilRef = soil ?? {
    hasData: false,
    macroRatings: {},
    deficientMicronutrients: [],
  };
  const sat: SatelliteRef = satellite ?? {
    hasData: false,
    vegetationHealth: null,
    lowVigor: false,
  };
  const w: WeatherRef = weather ?? { hasData: false, heavyRain: false };

  const primary = observation.primary;
  const severity = observation.severity;
  const area = observation.affectedArea;

  if (primary === null) {
    return {
      primaryDeficiency: null,
      secondaryDeficiency: null,
      status: "not_confirmed",
      confidence: clamp(observation.visualConfidence),
      severity,
      affectedArea: area,
      soilSupports: null,
      satelliteSupports: false,
      weatherSupports: false,
      diseaseConflict,
      needsTest: true,
      needsExpert: diseaseConflict,
    };
  }

  let confidence = observation.visualConfidence;
  const [soilDelta, soilSupports] = soilSignal(primary, s);
  confidence += soilDelta;

  let satelliteSupports = false;
  if (sat.hasData && MACRO.has(primary) && sat.lowVigor) {
    confidence += CORROBORATION_BOOST;
    satelliteSupports = true;
  }

  let weatherSupports = false;
  if (w.hasData && w.heavyRain && primary === "nitrogen") {
    confidence += CORROBORATION_BOOST;
    weatherSupports = true;
  }

  if (diseaseConflict) confidence -= DISEASE_CONFLICT_PENALTY;

  confidence = clamp(confidence);
  const corroborated =
    soilSupports === true || satelliteSupports || weatherSupports;

  let status: DeficiencyStatus;
  if (confidence >= CONFIDENCE_CONFIRM && corroborated) status = "confirmed";
  else if (confidence >= CONFIDENCE_POSSIBLE) status = "possible";
  else status = "not_confirmed";

  const micronutrientWithoutSoil = SOIL_MICRO.has(primary) && !s.hasData;
  const needsTest = status !== "confirmed" || micronutrientWithoutSoil;
  const needsExpert = diseaseConflict || severity === "severe";

  return {
    primaryDeficiency: primary,
    secondaryDeficiency: observation.secondary,
    status,
    confidence,
    severity: severity === "unknown" ? "moderate" : severity,
    affectedArea: area === "unknown" ? null : area,
    soilSupports,
    satelliteSupports,
    weatherSupports,
    diseaseConflict,
    needsTest,
    needsExpert,
  };
}

function rec(
  category: string,
  code: string,
  severity: string,
  nutrient: string | null = null,
): NutrientRecommendation {
  const priority =
    severity === REC_CRITICAL
      ? "high"
      : severity === REC_WARNING
        ? "medium"
        : "low";
  return { category, code, nutrient, severity, priority };
}

export function buildRecommendations(a: Assessment): NutrientRecommendation[] {
  const recs: NutrientRecommendation[] = [];
  const primary = a.primaryDeficiency;

  if (
    primary &&
    (a.status === "confirmed" || a.status === "possible") &&
    a.soilSupports !== false &&
    !a.diseaseConflict
  ) {
    const recSev = SEVERITY_TO_REC[a.severity] ?? REC_WARNING;
    recs.push(
      rec("nutrient", `nutrient.rec.${primary}.deficiency`, recSev, primary),
    );
  }

  if (a.status === "not_confirmed") {
    recs.push(rec("general", "nutrient.rec.general.not_confirmed", REC_INFO));
  }
  if (a.needsTest) {
    recs.push(rec("test", "nutrient.rec.test.soil_test", REC_WARNING));
  }
  if (a.needsExpert) {
    recs.push(rec("expert", "nutrient.rec.expert.consult", REC_WARNING));
  }
  if (
    a.status === "confirmed" &&
    (a.severity === "none" || a.severity === "mild")
  ) {
    recs.push(rec("monitor", "nutrient.rec.monitor.observe", REC_INFO));
  }
  return recs;
}

export function worstSeverity(recs: NutrientRecommendation[]): string | null {
  if (recs.length === 0) return null;
  return recs.reduce((w, r) =>
    (REC_ORDER[r.severity] ?? 0) > (REC_ORDER[w.severity] ?? 0) ? r : w,
  ).severity;
}
