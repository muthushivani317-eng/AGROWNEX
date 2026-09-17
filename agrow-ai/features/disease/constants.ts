import type { Severity } from './types';

export const DISEASE_STORE_KEY = 'agrowai.disease.reports';

export const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const MIN_DIMENSION_PX = 224;
export const MIN_IMAGE_BYTES = 2 * 1024;
export const MAX_IMAGE_BYTES = 12 * 1024 * 1024;

export const diseaseKeys = {
  all: ['disease'] as const,
  history: (farmId: string | null, unassignedOnly = false) =>
    ['disease', 'history', unassignedOnly ? 'unassigned' : (farmId ?? 'all')] as const,
  report: (id: string) => ['disease', 'report', id] as const,
};

/** Severity → AgBadge tone. */
export const SEVERITY_TONE: Record<Severity, 'neutral' | 'success' | 'warning' | 'danger'> = {
  none: 'success',
  low: 'success',
  moderate: 'warning',
  high: 'danger',
};

/** Quality issue code → i18n key (client + backend share the codes). */
export const QUALITY_ISSUE_KEY: Record<string, string> = {
  missing: 'disease.qualityMissing',
  too_small: 'disease.qualityTooSmall',
  too_large: 'disease.qualityTooLarge',
  unsupported_type: 'disease.qualityUnsupported',
  corrupted: 'disease.qualityCorrupted',
  blurry: 'disease.qualityBlurry',
  dark: 'disease.qualityDark',
  overexposed: 'disease.qualityOverexposed',
};
