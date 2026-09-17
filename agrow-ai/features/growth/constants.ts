import type { GrowthStage, PlantVigor, RiskLevel } from './types';

export const GROWTH_STORE_KEY = 'agrowai.growth.images';
export const GROWTH_SESSION_KEY = 'agrowai.growth.sessions';

export const growthKeys = {
  all: ['growth'] as const,
  history: (sessionId: string | null, farmId: string | null) =>
    ['growth', 'history', sessionId ?? 'all', farmId ?? 'all'] as const,
  timeline: (sessionId: string | null, farmId: string | null) =>
    ['growth', 'timeline', sessionId ?? 'latest', farmId ?? 'all'] as const,
  latest: ['growth', 'latest'] as const,
  session: (id: string) => ['growth', 'session', id] as const,
};

/** Growth stage → localized label key (under the `growth` namespace). */
export const STAGE_LABEL_KEY: Record<GrowthStage, string> = {
  germination: 'growth.stageGermination',
  seedling: 'growth.stageSeedling',
  vegetative: 'growth.stageVegetative',
  flowering: 'growth.stageFlowering',
  fruiting: 'growth.stageFruiting',
  maturity: 'growth.stageMaturity',
  harvest: 'growth.stageHarvest',
  unknown: 'growth.stageUnknown',
};

/** Plant vigour → localized label key. */
export const VIGOR_LABEL_KEY: Record<PlantVigor, string> = {
  poor: 'growth.vigorPoor',
  fair: 'growth.vigorFair',
  good: 'growth.vigorGood',
  excellent: 'growth.vigorExcellent',
  unknown: 'growth.vigorUnknown',
};

/** Vigour → AgBadge tone. */
export const VIGOR_TONE: Record<PlantVigor, 'neutral' | 'success' | 'warning' | 'danger'> = {
  poor: 'danger',
  fair: 'warning',
  good: 'success',
  excellent: 'success',
  unknown: 'neutral',
};

/** Risk level → localized label key + AgBadge tone. */
export const RISK_LABEL_KEY: Record<RiskLevel, string> = {
  low: 'growth.riskLow',
  moderate: 'growth.riskModerate',
  high: 'growth.riskHigh',
};

export const RISK_TONE: Record<RiskLevel, 'success' | 'warning' | 'danger'> = {
  low: 'success',
  moderate: 'warning',
  high: 'danger',
};
