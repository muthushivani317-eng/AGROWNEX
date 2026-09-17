import type {
  HealthModule,
  IssueSeverity,
  Priority,
  RiskLevel,
} from './types';

export const INTEL_DASHBOARD_CACHE_KEY = 'agrowai.intelligence.dashboard.cache';
export const INTEL_HISTORY_CACHE_KEY = 'agrowai.intelligence.history.cache';
export const INTEL_REPORT_CACHE_KEY = 'agrowai.intelligence.report.cache';
export const INTEL_LOCAL_KEY = 'agrowai.intelligence.local';
export const INTEL_OUTBOX_KEY = 'agrowai.intelligence.outbox';

export const DEFAULT_PAGE_SIZE = 20;

export const intelligenceKeys = {
  all: ['intelligence'] as const,
  dashboard: (farmId: string) => ['intelligence', 'dashboard', farmId] as const,
  history: (farmId: string) => ['intelligence', 'history', farmId] as const,
  report: (id: string) => ['intelligence', 'report', id] as const,
};

/** The six health-scoring modules shown on the health-score visualization, in order. */
export const HEALTH_MODULES: HealthModule[] = [
  'disease',
  'nutrient',
  'growth',
  'soil',
  'satellite',
  'weather',
];

export const MODULE_LABEL_KEY: Record<string, string> = {
  disease: 'intelligence.moduleDisease',
  nutrient: 'intelligence.moduleNutrient',
  soil: 'intelligence.moduleSoil',
  satellite: 'intelligence.moduleSatellite',
  weather: 'intelligence.moduleWeather',
  growth: 'intelligence.moduleGrowth',
  calendar: 'intelligence.moduleCalendar',
  expert: 'intelligence.moduleExpert',
};

/** Overall risk → chip tone + label. */
export const RISK_TONE: Record<RiskLevel, 'success' | 'info' | 'warning' | 'danger'> = {
  low: 'success',
  medium: 'info',
  high: 'warning',
  critical: 'danger',
};

export const RISK_LABEL_KEY: Record<RiskLevel, string> = {
  low: 'intelligence.riskLow',
  medium: 'intelligence.riskMedium',
  high: 'intelligence.riskHigh',
  critical: 'intelligence.riskCritical',
};

export const SEVERITY_TONE: Record<IssueSeverity, 'success' | 'info' | 'warning' | 'danger'> = {
  info: 'success',
  advice: 'info',
  warning: 'warning',
  critical: 'danger',
};

export const PRIORITY_TONE: Record<Priority, 'danger' | 'warning' | 'neutral'> = {
  high: 'danger',
  medium: 'warning',
  low: 'neutral',
};

export const PRIORITY_LABEL_KEY: Record<Priority, string> = {
  high: 'intelligence.priorityHigh',
  medium: 'intelligence.priorityMedium',
  low: 'intelligence.priorityLow',
};

/** A health sub-score band → bar tone (0-100). */
export function scoreTone(score: number | null): 'success' | 'warning' | 'danger' | 'neutral' {
  if (score === null) return 'neutral';
  if (score >= 80) return 'success';
  if (score >= 55) return 'warning';
  return 'danger';
}

/** Confidence bands (a report is never presented as certain). */
export const CONFIDENCE_STRONG = 70;
export const CONFIDENCE_MODERATE = 50;
