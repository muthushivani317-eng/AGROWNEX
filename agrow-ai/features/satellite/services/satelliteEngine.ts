import type { SatelliteAlert, Severity } from '../types';

/**
 * Client-side mirror of the backend Satellite Engine + Alert Engine (backend:
 * app/modules/satellite/{engine,alerts}.py). Same standard formulas and thresholds
 * so the local/offline provider classifies and alerts exactly like the server.
 * Never invents a missing value — an absent band gives ``null`` (docs/PRODUCT_RULES).
 */
const NDVI_BARE = 0.1;
const NDVI_VERY_LOW = 0.2;
const NDVI_LOW = 0.4;
const NDVI_MODERATE = 0.6;
const NDVI_GOOD = 0.8;
const NDMI_VERY_DRY = -0.2;
const NDMI_DRY = 0.0;
const NDMI_ADEQUATE = 0.2;
const NDMI_MOIST = 0.4;
const DELTA_IMPROVING = 0.05;
const DELTA_DECLINING = -0.05;
const DELTA_RAPID = -0.15;
const DELTA_ABNORMAL = -0.2;
const LOW_VIGOR = 0.3;
const MOISTURE_STRESS = 0.0;
const VARIATION_STD = 0.15;
const CLOUD_ADVISORY = 25.0;

const SEVERITY_ORDER: Record<string, number> = { info: 0, advice: 1, warning: 2, critical: 3 };

export interface Bands {
  red?: number | null;
  nir?: number | null;
  redEdge?: number | null;
  swir?: number | null;
  blue?: number | null;
}

export interface Indices {
  ndvi: number | null;
  ndre: number | null;
  evi: number | null;
  ndmi: number | null;
}

function ratio(a: number | null | undefined, b: number | null | undefined): number | null {
  if (a === null || a === undefined || b === null || b === undefined) return null;
  const denom = a + b;
  return denom === 0 ? null : Math.round(((a - b) / denom) * 10000) / 10000;
}

export function computeIndices(bands: Bands): Indices {
  let evi: number | null = null;
  if (bands.nir != null && bands.red != null && bands.blue != null) {
    const denom = bands.nir + 6 * bands.red - 7.5 * bands.blue + 1;
    if (denom !== 0) {
      evi = Math.round((2.5 * (bands.nir - bands.red)) / denom * 10000) / 10000;
    }
  }
  return {
    ndvi: ratio(bands.nir, bands.red),
    ndre: ratio(bands.nir, bands.redEdge),
    evi,
    ndmi: ratio(bands.nir, bands.swir),
  };
}

export function classifyHealth(ndvi: number | null): string {
  if (ndvi === null) return 'unknown';
  if (ndvi < NDVI_BARE) return 'bare';
  if (ndvi < NDVI_VERY_LOW) return 'very_low';
  if (ndvi < NDVI_LOW) return 'low';
  if (ndvi < NDVI_MODERATE) return 'moderate';
  if (ndvi < NDVI_GOOD) return 'good';
  return 'very_good';
}

export function classifyMoisture(ndmi: number | null): string {
  if (ndmi === null) return 'unknown';
  if (ndmi < NDMI_VERY_DRY) return 'very_dry';
  if (ndmi < NDMI_DRY) return 'dry';
  if (ndmi < NDMI_ADEQUATE) return 'adequate';
  if (ndmi < NDMI_MOIST) return 'moist';
  return 'wet';
}

export function classifyTrend(
  ndvi: number | null,
  previous: number | null,
): { trend: string; delta: number | null } {
  if (ndvi === null || previous === null) return { trend: 'unknown', delta: null };
  const delta = Math.round((ndvi - previous) * 10000) / 10000;
  if (delta >= DELTA_IMPROVING) return { trend: 'improving', delta };
  if (delta <= DELTA_DECLINING) return { trend: 'declining', delta };
  return { trend: 'stable', delta };
}

export function classifyStress(ndvi: number | null, trend: string, delta: number | null): string {
  if (ndvi === null) return 'unknown';
  const order = ['none', 'mild', 'moderate', 'severe'];
  let base = 'none';
  if (ndvi < NDVI_VERY_LOW) base = 'severe';
  else if (ndvi < NDVI_LOW) base = 'moderate';
  else if (ndvi < NDVI_MODERATE) base = 'mild';
  if (delta !== null && delta <= DELTA_RAPID) {
    base = order[Math.min(order.indexOf(base) + 1, order.length - 1)];
  } else if (trend === 'declining' && base === 'none') {
    base = 'mild';
  }
  return base;
}

export interface Assessment {
  ndvi: number | null;
  ndre: number | null;
  evi: number | null;
  ndmi: number | null;
  vegetationHealth: string;
  stressLevel: string;
  moistureStatus: string;
  trend: string;
  ndviDelta: number | null;
  hasValues: boolean;
}

export function assess(indices: Indices, previousNdvi: number | null = null): Assessment {
  const { trend, delta } = classifyTrend(indices.ndvi, previousNdvi);
  return {
    ...indices,
    vegetationHealth: classifyHealth(indices.ndvi),
    stressLevel: classifyStress(indices.ndvi, trend, delta),
    moistureStatus: classifyMoisture(indices.ndmi),
    trend,
    ndviDelta: delta,
    hasValues: [indices.ndvi, indices.ndre, indices.evi, indices.ndmi].some((v) => v !== null),
  };
}

export function computeConfidence(cloudCover: number | null, isSample = false): number {
  const base =
    cloudCover === null ? 50 : Math.max(10, Math.min(99, Math.round(100 - cloudCover * 1.5)));
  return isSample ? Math.min(base, 55) : base;
}

// --------------------------------------------------------------------------- //
// Alert engine mirror
// --------------------------------------------------------------------------- //
export interface AlertContext {
  status: string;
  unavailableReason?: string;
  cloudCover?: number | null;
  ndvi?: number | null;
  ndmi?: number | null;
  ndviDelta?: number | null;
  trend?: string;
  ndviStd?: number | null;
}

function alert(
  category: string,
  key: string,
  severity: Severity,
  value: number | null = null,
): SatelliteAlert {
  const priority = severity === 'critical' ? 'high' : severity === 'warning' ? 'medium' : 'low';
  return { code: `satellite.alert.${key}`, category, severity, priority, value, params: {} };
}

export function buildAlerts(ctx: AlertContext): SatelliteAlert[] {
  const out: SatelliteAlert[] = [];
  if (ctx.status === 'unavailable') {
    if (ctx.unavailableReason === 'cloud_cover') {
      out.push(alert('imagery', 'cloud_obstruction', 'warning', ctx.cloudCover ?? null));
    } else if (['no_imagery', 'acquisition_delay', 'provider_error'].includes(ctx.unavailableReason ?? '')) {
      out.push(alert('imagery', 'missing_imagery', 'warning'));
    }
    return out;
  }
  if (ctx.cloudCover != null && ctx.cloudCover >= CLOUD_ADVISORY) {
    out.push(alert('imagery', 'cloud_obstruction', 'advice', ctx.cloudCover));
  }
  const delta = ctx.ndviDelta;
  if (delta != null) {
    if (delta <= DELTA_ABNORMAL) out.push(alert('seasonal', 'abnormal_seasonal_change', 'critical', delta));
    else if (delta <= DELTA_RAPID) out.push(alert('vegetation', 'rapid_ndvi_drop', 'critical', delta));
    else if (delta <= DELTA_DECLINING) {
      if (ctx.ndvi != null && ctx.ndvi >= NDVI_LOW) {
        out.push(alert('vegetation', 'early_vegetation_decline', 'advice', delta));
      } else {
        out.push(alert('vegetation', 'vegetation_decline', 'warning', delta));
      }
    }
  }
  if (ctx.ndvi != null && ctx.ndvi < LOW_VIGOR) out.push(alert('vegetation', 'low_vigor', 'warning', ctx.ndvi));
  if (ctx.ndmi != null && ctx.ndmi < MOISTURE_STRESS) out.push(alert('moisture', 'moisture_stress', 'warning', ctx.ndmi));
  if (ctx.ndviStd != null && ctx.ndviStd >= VARIATION_STD) {
    out.push(alert('variation', 'large_field_variation', 'advice', ctx.ndviStd));
  }
  return out;
}

export function worstSeverity(alerts: SatelliteAlert[]): string | null {
  if (alerts.length === 0) return null;
  return alerts.reduce((w, a) => (SEVERITY_ORDER[a.severity] > SEVERITY_ORDER[w.severity] ? a : w)).severity;
}
