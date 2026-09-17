import type { DeficiencyStatus, Nutrient, Severity } from './types';

export const NUT_HISTORY_CACHE_KEY = 'agrowai.nutrient.history.cache';
export const NUT_LATEST_CACHE_KEY = 'agrowai.nutrient.latest.cache';
export const NUT_REPORT_CACHE_KEY = 'agrowai.nutrient.report.cache';
export const NUT_LOCAL_KEY = 'agrowai.nutrient.local';
export const NUT_OUTBOX_KEY = 'agrowai.nutrient.outbox';

export const DEFAULT_PAGE_SIZE = 20;

export const nutrientKeys = {
  all: ['nutrient'] as const,
  history: (farmId: string) => ['nutrient', 'history', farmId] as const,
  latest: (farmId: string) => ['nutrient', 'latest', farmId] as const,
  recommendations: (farmId: string) => ['nutrient', 'recommendations', farmId] as const,
  report: (id: string) => ['nutrient', 'report', id] as const,
};

export const NUTRIENTS: Nutrient[] = [
  'nitrogen',
  'phosphorus',
  'potassium',
  'sulphur',
  'calcium',
  'magnesium',
  'iron',
  'zinc',
  'boron',
  'copper',
  'manganese',
  'molybdenum',
  'chlorine',
];

/** Localization key for a nutrient name (``nutrient.name.<nutrient>``). */
export function nutrientLabelKey(nutrient: string): string {
  return `nutrient.name.${nutrient}`;
}

/** Localization key for a visible symptom (``nutrient.symptom.<code>``). */
export function symptomLabelKey(code: string): string {
  return `nutrient.symptom.${code}`;
}

export const STATUS_LABEL_KEY: Record<DeficiencyStatus, string> = {
  confirmed: 'nutrient.status.confirmed',
  possible: 'nutrient.status.possible',
  not_confirmed: 'nutrient.status.not_confirmed',
};

export const STATUS_TONE: Record<DeficiencyStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  confirmed: 'danger', // a confirmed deficiency needs action
  possible: 'warning',
  not_confirmed: 'neutral',
};

export const SEVERITY_LABEL_KEY: Record<Severity, string> = {
  none: 'nutrient.severity.none',
  mild: 'nutrient.severity.mild',
  moderate: 'nutrient.severity.moderate',
  severe: 'nutrient.severity.severe',
  unknown: 'nutrient.severity.unknown',
};

export const SEVERITY_TONE: Record<Severity, 'success' | 'warning' | 'danger' | 'neutral'> = {
  none: 'success',
  mild: 'warning',
  moderate: 'warning',
  severe: 'danger',
  unknown: 'neutral',
};

export const REC_SEVERITY_TONE: Record<string, 'info' | 'success' | 'warning' | 'danger'> = {
  info: 'info',
  advice: 'info',
  warning: 'warning',
  critical: 'danger',
};

/** Client-side quality-issue → localization key (reused disease vocabulary). */
export const QUALITY_ISSUE_KEY: Record<string, string> = {
  too_small: 'nutrient.qualityTooSmall',
  too_large: 'nutrient.qualityTooLarge',
  unsupported_type: 'nutrient.qualityUnsupported',
  blurry: 'nutrient.qualityBlurry',
  dark: 'nutrient.qualityDark',
  overexposed: 'nutrient.qualityOverexposed',
};

export const CONFIDENCE_CONFIRM = 75;
export const CONFIDENCE_POSSIBLE = 50;
