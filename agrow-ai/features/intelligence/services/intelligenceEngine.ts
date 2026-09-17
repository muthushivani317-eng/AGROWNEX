/**
 * Client mirror of the Crop Intelligence Engine (docs: HEALTH SCORING → DECISION →
 * RECOMMENDATION). Pure and deterministic — the exact same transparent weights,
 * thresholds and cross-module rules as the FastAPI engine, so the offline provider
 * reasons identically to the backend. Missing modules never invent values; they lower
 * confidence. No I/O, no side effects.
 */
import type {
  DiseaseSignal,
  GrowthSignal,
  HealthScores,
  IntelligenceInputs,
  IssueSeverity,
  NutrientSignal,
  Priority,
  PriorityIssue,
  Recommendation,
  RiskLevel,
  SatelliteSignal,
  SoilSignal,
  WeatherSignal,
} from '../types';

// --------------------------------------------------------------------------- //
// Weights & thresholds (mirror of the backend constants).
// --------------------------------------------------------------------------- //
const MODULE_WEIGHTS: Record<string, number> = {
  disease: 0.22,
  nutrient: 0.18,
  growth: 0.2,
  soil: 0.15,
  satellite: 0.15,
  weather: 0.1,
};

const MODULE_BASE_CONFIDENCE: Record<string, number> = {
  weather: 82,
  growth: 70,
  soil: 60,
};

const COVERAGE_WEIGHT = 0.55;
const MODULE_CONFIDENCE_WEIGHT = 0.45;

const RISK_LOW_MIN = 80;
const RISK_MEDIUM_MIN = 65;
const RISK_HIGH_MIN = 45;
const HEALTHY_MIN = 80;
const LOW_CONFIDENCE = 50;
const MIN_OVERALL_EVIDENCE_MODULES = 2;

const DISEASE_SEVERITY_PENALTY: Record<string, number> = {
  none: 0,
  low: 20,
  moderate: 45,
  high: 75,
};
const NUTRIENT_SEVERITY_PENALTY: Record<string, number> = {
  none: 0,
  mild: 20,
  moderate: 45,
  severe: 70,
  unknown: 25,
};
const NUTRIENT_NOT_CONFIRMED_PENALTY = 12;
const NEEDS_EXPERT_CAP = 60;

const VEGETATION_HEALTH_SCORE: Record<string, number> = {
  bare: 12,
  very_low: 28,
  low: 48,
  moderate: 66,
  good: 85,
  very_good: 95,
};

const GROWTH_RISK_SCORE: Record<string, number> = { low: 82, medium: 62, high: 42 };

const WEATHER_PENALTY: Record<string, number> = {
  'heavy_rain.severe': 18,
  'heavy_rain.expected': 14,
  'wind.strong': 10,
  'heat_stress.extreme': 18,
  'heat_stress.high': 10,
  'cold.frost': 14,
  'cold.low': 8,
};

const RISK_ORDER: Record<RiskLevel, number> = { low: 0, medium: 1, high: 2, critical: 3 };
const RISK_BY_ORDER: Record<number, RiskLevel> = { 0: 'low', 1: 'medium', 2: 'high', 3: 'critical' };
const SEVERITY_ORDER: Record<IssueSeverity, number> = { info: 0, advice: 1, warning: 2, critical: 3 };
const PRIORITY_ORDER: Record<Priority, number> = { high: 0, medium: 1, low: 2 };

const MAX_RECOMMENDATIONS = 5;

function clamp(value: number, lo = 0, hi = 100): number {
  return Math.round(Math.max(lo, Math.min(hi, value)));
}

// --------------------------------------------------------------------------- //
// Per-module sub-scores
// --------------------------------------------------------------------------- //
export function diseaseScore(sig: DiseaseSignal): number {
  const base = DISEASE_SEVERITY_PENALTY[sig.severity ?? 'moderate'] ?? 45;
  const conf = sig.confidence ?? 60;
  let score = 100 - (base * Math.max(conf, 40)) / 100;
  if (sig.needsExpert) score = Math.min(score, NEEDS_EXPERT_CAP);
  return clamp(score);
}

export function nutrientScore(sig: NutrientSignal): number {
  if (sig.primary === null || sig.status === 'not_confirmed') {
    return clamp(100 - NUTRIENT_NOT_CONFIRMED_PENALTY);
  }
  const base = NUTRIENT_SEVERITY_PENALTY[sig.severity ?? 'unknown'] ?? 25;
  const factor = sig.status === 'confirmed' ? 1.0 : 0.6;
  return clamp(100 - base * factor);
}

export function soilScore(sig: SoilSignal): number | null {
  if (!sig.hasData) return null;
  let score = 100;
  for (const [rating, low, medium] of [
    [sig.nitrogen, 18, 8],
    [sig.phosphorus, 15, 6],
    [sig.potassium, 15, 6],
  ] as const) {
    if (rating === 'low') score -= low;
    else if (rating === 'medium') score -= medium;
  }
  if (sig.organicCarbon === 'low') score -= 10;
  if (sig.phClass === 'strongly_acidic' || sig.phClass === 'strongly_alkaline') score -= 15;
  else if (sig.phClass === 'acidic' || sig.phClass === 'alkaline') score -= 8;
  if (sig.salinity === 'high') score -= 20;
  else if (sig.salinity === 'medium') score -= 10;
  score -= 8 * (sig.deficientMicronutrients?.length ?? 0);
  return clamp(score);
}

export function satelliteScore(sig: SatelliteSignal): number {
  let base = VEGETATION_HEALTH_SCORE[sig.vegetationHealth ?? ''];
  if (base === undefined) {
    if (sig.ndvi === null) base = 60;
    else if (sig.ndvi < 0.2) base = 25;
    else if (sig.ndvi < 0.4) base = 48;
    else if (sig.ndvi < 0.6) base = 66;
    else if (sig.ndvi < 0.8) base = 85;
    else base = 92;
  }
  let score = base;
  if (sig.stressLevel === 'severe') score -= 20;
  else if (sig.stressLevel === 'moderate') score -= 10;
  if (sig.trend === 'declining') score -= 8;
  else if (sig.trend === 'improving') score += 5;
  if (sig.moistureStatus === 'very_dry') score -= 8;
  else if (sig.moistureStatus === 'dry') score -= 4;
  return clamp(score);
}

export function weatherScore(sig: WeatherSignal): number {
  let score = 92;
  for (const code of sig.insightCodes) score -= WEATHER_PENALTY[code] ?? 0;
  if (sig.rainProbabilityPct != null && sig.rainProbabilityPct >= 80) score -= 5;
  return clamp(score, 40);
}

export function growthScore(sig: GrowthSignal): number {
  let base = sig.healthScore != null ? sig.healthScore : GROWTH_RISK_SCORE[sig.riskLevel ?? 'medium'] ?? 62;
  if (sig.healthDelta != null) base += Math.max(-15, Math.min(10, sig.healthDelta));
  return clamp(base);
}

function moduleConfidence(inputs: IntelligenceInputs): Record<string, number> {
  const conf: Record<string, number> = {};
  if (inputs.disease) conf.disease = inputs.disease.confidence || 60;
  if (inputs.nutrient) conf.nutrient = inputs.nutrient.confidence || 55;
  if (inputs.soil?.hasData) conf.soil = inputs.soil.confidence || MODULE_BASE_CONFIDENCE.soil;
  if (inputs.satellite) conf.satellite = inputs.satellite.confidence || 70;
  if (inputs.weather) conf.weather = MODULE_BASE_CONFIDENCE.weather;
  if (inputs.growth) conf.growth = MODULE_BASE_CONFIDENCE.growth;
  return conf;
}

export function computeHealth(inputs: IntelligenceInputs): HealthScores & { sourcesUsed: string[] } {
  const scores: Record<string, number | null> = {
    disease: inputs.disease ? diseaseScore(inputs.disease) : null,
    nutrient: inputs.nutrient ? nutrientScore(inputs.nutrient) : null,
    soil: inputs.soil ? soilScore(inputs.soil) : null,
    satellite: inputs.satellite ? satelliteScore(inputs.satellite) : null,
    weather: inputs.weather ? weatherScore(inputs.weather) : null,
    growth: inputs.growth ? growthScore(inputs.growth) : null,
  };
  const present = Object.entries(scores).filter(([, s]) => s !== null) as [string, number][];

  let overall: number | null = null;
  if (present.length >= MIN_OVERALL_EVIDENCE_MODULES) {
    const wsum = present.reduce((a, [c]) => a + MODULE_WEIGHTS[c], 0);
    const weighted = present.reduce((a, [c, s]) => a + MODULE_WEIGHTS[c] * s, 0);
    overall = clamp(weighted / wsum);
  }

  const modConf = moduleConfidence(inputs);
  const modConfValues = Object.values(modConf);
  const coverage = present.length / Object.keys(MODULE_WEIGHTS).length;
  const confAvg = modConfValues.length
    ? modConfValues.reduce((a, b) => a + b, 0) / modConfValues.length
    : 0;
  const confidence = present.length
    ? clamp(COVERAGE_WEIGHT * coverage * 100 + MODULE_CONFIDENCE_WEIGHT * confAvg)
    : 0;

  return {
    overallHealthScore: overall,
    confidence,
    diseaseScore: scores.disease,
    nutrientScore: scores.nutrient,
    soilScore: scores.soil,
    satelliteScore: scores.satellite,
    weatherScore: scores.weather,
    growthScore: scores.growth,
    sourcesUsed: present.map(([c]) => c),
  };
}

// --------------------------------------------------------------------------- //
// Decision engine — priority issues + risk
// --------------------------------------------------------------------------- //
function issue(code: string, severity: IssueSeverity, ...modules: string[]): PriorityIssue {
  return { code: `intelligence.issue.${code}`, severity, modules };
}

export function detectIssues(
  inputs: IntelligenceInputs,
  scores: HealthScores,
): PriorityIssue[] {
  const issues: PriorityIssue[] = [];

  const d = inputs.disease;
  if (d && scores.diseaseScore !== null && scores.diseaseScore < 70) {
    const sev: IssueSeverity =
      d.severity === 'high' ? 'critical' : d.severity === 'moderate' ? 'warning' : 'advice';
    issues.push(issue('disease_active', sev, 'disease'));
  }

  const n = inputs.nutrient;
  if (n && n.primary && (n.status === 'confirmed' || n.status === 'possible')) {
    const sev: IssueSeverity =
      n.status === 'confirmed' && n.severity === 'severe'
        ? 'critical'
        : n.status === 'confirmed'
          ? 'warning'
          : 'advice';
    issues.push(issue('nutrient_deficiency', sev, 'nutrient', 'soil'));
  }

  const s = inputs.soil;
  if (s?.hasData) {
    const lows = [s.nitrogen, s.phosphorus, s.potassium].filter((r) => r === 'low').length;
    if (s.salinity === 'high') issues.push(issue('soil_salinity', 'warning', 'soil'));
    if (lows || (s.deficientMicronutrients?.length ?? 0) > 0) {
      const sev: IssueSeverity =
        lows >= 2 || (s.deficientMicronutrients?.length ?? 0) > 0 ? 'warning' : 'advice';
      const code = s.nitrogen === 'low' ? 'soil_low_nitrogen' : 'soil_deficiency';
      issues.push(issue(code, sev, 'soil'));
    }
  }

  const sat = inputs.satellite;
  if (sat) {
    const declining =
      sat.trend === 'declining' ||
      ['bare', 'very_low', 'low'].includes(sat.vegetationHealth ?? '') ||
      (sat.alertCodes?.length ?? 0) > 0;
    if (declining) {
      const sev: IssueSeverity = sat.stressLevel === 'severe' ? 'critical' : 'warning';
      issues.push(issue('vegetation_decline', sev, 'satellite'));
    }
    if (sat.moistureStatus === 'very_dry' || sat.moistureStatus === 'dry') {
      const sev: IssueSeverity = sat.moistureStatus === 'very_dry' ? 'warning' : 'advice';
      issues.push(issue('moisture_stress', sev, 'satellite', 'weather'));
    }
  }

  const w = inputs.weather;
  if (w) {
    if (w.insightCodes.some((c) => c.startsWith('heavy_rain'))) {
      issues.push(issue('weather_heavy_rain', 'warning', 'weather'));
    }
    if (w.insightCodes.some((c) => c.startsWith('heat_stress'))) {
      issues.push(issue('weather_heat', 'warning', 'weather'));
    }
  }

  const g = inputs.growth;
  if (g && (g.riskLevel === 'high' || (g.healthDelta ?? 0) <= -5)) {
    issues.push(issue('growth_decline', 'warning', 'growth'));
  }

  const cal = inputs.calendar;
  if (cal && cal.missed > 0) {
    issues.push(issue('missed_tasks', cal.missed >= 3 ? 'warning' : 'advice', 'calendar'));
  }

  issues.sort((a, b) => SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity]);
  return issues;
}

function baseRisk(overall: number | null): RiskLevel {
  if (overall === null || overall >= RISK_LOW_MIN) return 'low';
  if (overall >= RISK_MEDIUM_MIN) return 'medium';
  if (overall >= RISK_HIGH_MIN) return 'high';
  return 'critical';
}

function forcesCritical(inputs: IntelligenceInputs): boolean {
  const { disease: d, nutrient: n, soil: s, satellite: sat } = inputs;
  if (d && d.severity === 'high' && (d.confidence ?? 0) >= 70) return true;
  if (n && n.status === 'confirmed' && n.severity === 'severe') return true;
  if (s && s.salinity === 'high') return true;
  if (sat && sat.stressLevel === 'severe') return true;
  return false;
}

export function assessRisk(
  inputs: IntelligenceInputs,
  scores: HealthScores,
  issues: PriorityIssue[],
): RiskLevel {
  let order = RISK_ORDER[baseRisk(scores.overallHealthScore)];

  if (forcesCritical(inputs)) {
    order = Math.max(order, RISK_ORDER.critical);
  } else if (issues.some((i) => i.severity === 'critical')) {
    order = Math.max(order, RISK_ORDER.high);
  }

  const adverseWeather =
    !!inputs.weather &&
    inputs.weather.insightCodes.some(
      (c) => c.startsWith('heavy_rain') || c.startsWith('heat_stress') || c.startsWith('cold'),
    );
  const cropProblem = issues.some(
    (i) => i.code.endsWith('disease_active') || i.code.endsWith('vegetation_decline'),
  );
  if (adverseWeather && cropProblem) order = Math.max(order, RISK_ORDER.medium);

  return RISK_BY_ORDER[order];
}

// --------------------------------------------------------------------------- //
// Recommendation engine
// --------------------------------------------------------------------------- //
function hasIssue(issues: PriorityIssue[], suffix: string): boolean {
  return issues.some((i) => i.code.endsWith(suffix));
}

export function generateRecommendations(
  inputs: IntelligenceInputs,
  scores: HealthScores,
  issues: PriorityIssue[],
  risk: RiskLevel,
): Recommendation[] {
  const drafts: Recommendation[] = [];
  const add = (key: string, priority: Priority, category: string, ...modules: string[]) => {
    const code = `intelligence.rec.${key}`;
    if (drafts.some((d) => d.code === code)) return;
    drafts.push({ code, priority, category, modules });
  };

  const d = inputs.disease;
  const diseaseActive = hasIssue(issues, 'disease_active');
  const diseaseHighConf = !!d && (d.confidence ?? 0) >= 60;
  const heavyRain = !!inputs.weather && inputs.weather.insightCodes.some((c) => c.startsWith('heavy_rain'));
  const vegDecline = hasIssue(issues, 'vegetation_decline');
  const moistureStress = hasIssue(issues, 'moisture_stress');
  const nitrogenLow = !!inputs.soil && inputs.soil.hasData && inputs.soil.nitrogen === 'low';
  const nutrientActive =
    !!inputs.nutrient &&
    inputs.nutrient.primary !== null &&
    (inputs.nutrient.status === 'confirmed' || inputs.nutrient.status === 'possible');

  if (diseaseActive && diseaseHighConf) add('treat_disease', 'high', 'treatment', 'disease');

  if (nitrogenLow && (nutrientActive || inputs.nutrient?.primary === 'nitrogen')) {
    add('address_nitrogen', 'high', 'nutrition', 'soil', 'nutrient');
  } else if (nutrientActive) {
    const priority: Priority = inputs.nutrient!.status === 'confirmed' ? 'high' : 'medium';
    add('address_nutrient', priority, 'nutrition', 'nutrient');
  }

  if (vegDecline && !diseaseActive && !nutrientActive) {
    add('check_irrigation', 'high', 'irrigation', 'satellite');
  }

  if (heavyRain && (diseaseActive || (d && (scores.diseaseScore ?? 100) < 80))) {
    add('preventive_advisory', 'high', 'preventive', 'weather', 'disease');
  }

  if (moistureStress && !heavyRain) add('irrigate', 'medium', 'irrigation', 'satellite');

  if (inputs.calendar && inputs.calendar.missed > 0) add('catch_up_tasks', 'medium', 'task', 'calendar');

  if (scores.confidence < LOW_CONFIDENCE) add('gather_more_data', 'medium', 'data');

  if (risk === 'high' || risk === 'critical') {
    if (inputs.expert?.openConsultation) add('await_expert', 'low', 'expert', 'expert');
    else add('consult_expert', 'high', 'expert', 'expert');
  }

  if (issues.length === 0 && scores.overallHealthScore !== null && scores.overallHealthScore >= HEALTHY_MIN) {
    add('maintain', 'low', 'maintain');
  }

  drafts.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]);
  return drafts.slice(0, MAX_RECOMMENDATIONS);
}
