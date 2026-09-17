import type { SoilAssessment, SoilRecommendation, SoilValues } from '../types';

/**
 * Client-side mirror of the backend Soil Engine (backend:
 * app/modules/soil/engine.py). Same Soil Health Card thresholds → the local/offline
 * provider classifies and advises exactly like the server. Generic agronomic advice
 * only — no commercial brands, never a fabricated value (docs/PRODUCT_RULES.md).
 */
const PH_STRONGLY_ACIDIC = 5.5;
const PH_ACIDIC = 6.5;
const PH_NEUTRAL_MAX = 7.5;
const PH_STRONGLY_ALKALINE = 8.5;
const OC_LOW = 0.5;
const OC_MEDIUM = 0.75;
const N_LOW = 280;
const N_MEDIUM = 560;
const P_LOW = 10;
const P_MEDIUM = 25;
const K_LOW = 120;
const K_MEDIUM = 280;
const EC_NORMAL = 1.0;
const EC_HIGH = 2.0;

const MICRONUTRIENT_FLOORS: Record<string, number> = {
  zinc: 0.6,
  iron: 4.5,
  manganese: 2.0,
  copper: 0.2,
  boron: 0.5,
};

const UNITS: Record<string, string> = {
  ph: '',
  organic_carbon: '%',
  nitrogen: 'kg/ha',
  phosphorus: 'kg/ha',
  potassium: 'kg/ha',
  ec_salinity: 'dS/m',
  water_holding_capacity: '%',
};

const SEVERITY_ORDER: Record<string, number> = {
  info: 0,
  advice: 1,
  warning: 2,
  critical: 3,
};

const num = (v: number | null | undefined): number | null =>
  v === undefined || v === null ? null : v;

export function classifyPh(ph: number | null): string {
  if (ph === null) return 'unknown';
  if (ph < PH_STRONGLY_ACIDIC) return 'strongly_acidic';
  if (ph < PH_ACIDIC) return 'acidic';
  if (ph <= PH_NEUTRAL_MAX) return 'neutral';
  if (ph <= PH_STRONGLY_ALKALINE) return 'alkaline';
  return 'strongly_alkaline';
}

function band(value: number | null, low: number, medium: number): string {
  if (value === null) return 'unknown';
  if (value < low) return 'low';
  if (value < medium) return 'medium';
  return 'high';
}

function classifySalinity(ec: number | null): string {
  if (ec === null) return 'unknown';
  if (ec < EC_NORMAL) return 'optimal';
  if (ec < EC_HIGH) return 'medium';
  return 'high';
}

function deficientMicronutrients(values: Record<string, number> | null | undefined): string[] {
  if (!values) return [];
  return Object.entries(MICRONUTRIENT_FLOORS)
    .filter(([name, floor]) => values[name] !== undefined && values[name] < floor)
    .map(([name]) => name);
}

export function assess(values: SoilValues): SoilAssessment {
  const ph = num(values.ph);
  const oc = num(values.organicCarbon);
  const n = num(values.nitrogen);
  const p = num(values.phosphorus);
  const k = num(values.potassium);
  const ec = num(values.ecSalinity);
  const hasAny = [ph, oc, n, p, k, ec].some((v) => v !== null);
  return {
    phClass: classifyPh(ph),
    organicCarbon: band(oc, OC_LOW, OC_MEDIUM),
    nitrogen: band(n, N_LOW, N_MEDIUM),
    phosphorus: band(p, P_LOW, P_MEDIUM),
    potassium: band(k, K_LOW, K_MEDIUM),
    salinity: classifySalinity(ec),
    deficientMicronutrients: deficientMicronutrients(values.micronutrients),
    hasAnyValue: hasAny,
  };
}

function priorityFor(severity: string): string {
  if (severity === 'critical') return 'high';
  if (severity === 'warning') return 'medium';
  return 'low';
}

function rec(
  category: string,
  key: string,
  severity: SoilRecommendation['severity'],
  parameter: string | null = null,
  rating: string | null = null,
  value: number | null = null,
): SoilRecommendation {
  return {
    category,
    code: `soil.rec.${category}.${key}`,
    severity,
    priority: priorityFor(severity),
    parameter,
    rating,
    value,
    unit: parameter ? UNITS[parameter] || null : null,
  };
}

const NUTRIENT_RULE: Record<string, [string, SoilRecommendation['severity']]> = {
  low: ['low', 'warning'],
  medium: ['medium', 'advice'],
  high: ['high', 'info'],
};

const PH_RULE: Record<string, [string, SoilRecommendation['severity']]> = {
  strongly_acidic: ['strongly_acidic', 'critical'],
  acidic: ['acidic', 'warning'],
  neutral: ['neutral', 'info'],
  alkaline: ['alkaline', 'warning'],
  strongly_alkaline: ['strongly_alkaline', 'critical'],
};

/** Generic agronomic advice from the assessed values (pure, no brands). */
export function buildRecommendations(
  values: SoilValues,
  soilType?: string | null,
): SoilRecommendation[] {
  const a = assess(values);
  const out: SoilRecommendation[] = [];

  if (PH_RULE[a.phClass]) {
    const [key, sev] = PH_RULE[a.phClass];
    out.push(rec('ph', key, sev, 'ph', a.phClass, num(values.ph)));
  }

  for (const [category, param, rating, value] of [
    ['organic_carbon', 'organic_carbon', a.organicCarbon, num(values.organicCarbon)],
    ['nitrogen', 'nitrogen', a.nitrogen, num(values.nitrogen)],
    ['phosphorus', 'phosphorus', a.phosphorus, num(values.phosphorus)],
    ['potassium', 'potassium', a.potassium, num(values.potassium)],
  ] as const) {
    if (NUTRIENT_RULE[rating]) {
      const [key, sev] = NUTRIENT_RULE[rating];
      out.push(rec(category, key, sev, param, rating, value));
    }
  }

  for (const element of a.deficientMicronutrients) {
    out.push(rec('micronutrient', 'deficient', 'warning', element, 'low'));
  }

  if (a.salinity === 'high') {
    out.push(rec('general', 'salinity_high', 'critical', 'ec_salinity', a.salinity, num(values.ecSalinity)));
  } else if (a.salinity === 'medium') {
    out.push(rec('general', 'salinity_medium', 'warning', 'ec_salinity', a.salinity, num(values.ecSalinity)));
  }

  if (values.drainage === 'poor') {
    out.push(rec('drainage', 'poor', 'warning', 'drainage', values.drainage));
  } else if (values.drainage === 'excessive') {
    out.push(rec('drainage', 'excessive', 'advice', 'drainage', values.drainage));
  }

  const type = (soilType ?? '').toLowerCase();
  if (type.includes('sand')) {
    out.push(rec('water_holding', 'sandy', 'advice', 'soil_type', type));
  } else if (type.includes('clay')) {
    out.push(rec('drainage', 'clay', 'advice', 'soil_type', type));
  }

  if (!a.hasAnyValue && a.deficientMicronutrients.length === 0) {
    out.push(rec('general', 'no_data', 'advice'));
  }

  return out;
}

export function worstSeverity(recs: SoilRecommendation[]): string | null {
  if (recs.length === 0) return null;
  return recs.reduce((worst, r) =>
    SEVERITY_ORDER[r.severity] > SEVERITY_ORDER[worst.severity] ? r : worst,
  ).severity;
}
