import type { MemoryImportance, MemoryLinkType, ObservationKind } from './types';

export const MEMORY_DASHBOARD_CACHE_KEY = 'agrowai.memory.dashboard.cache';
export const MEMORY_HISTORY_CACHE_KEY = 'agrowai.memory.history.cache';
export const MEMORY_SUMMARY_CACHE_KEY = 'agrowai.memory.summary.cache';
export const MEMORY_DETAIL_CACHE_KEY = 'agrowai.memory.detail.cache';
export const MEMORY_LOCAL_KEY = 'agrowai.memory.local';
export const MEMORY_OUTBOX_KEY = 'agrowai.memory.outbox';

export const DEFAULT_PAGE_SIZE = 20;

export const memoryKeys = {
  all: ['memory'] as const,
  dashboard: (farmId: string) => ['memory', 'dashboard', farmId] as const,
  history: (farmId: string, filterKey: string) =>
    ['memory', 'history', farmId, filterKey] as const,
  summary: (farmId: string) => ['memory', 'summary', farmId] as const,
  detail: (id: string) => ['memory', 'detail', id] as const,
};

export const IMPORTANCE_SCORE: Record<MemoryImportance, number> = {
  low: 25,
  medium: 50,
  high: 75,
  critical: 95,
};

export const IMPORTANCE_ORDER: Record<MemoryImportance, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

/** Importance → chip tone. */
export const IMPORTANCE_TONE: Record<MemoryImportance, 'neutral' | 'info' | 'warning' | 'danger'> = {
  low: 'neutral',
  medium: 'info',
  high: 'warning',
  critical: 'danger',
};

export const IMPORTANCE_LABEL_KEY: Record<MemoryImportance, string> = {
  low: 'memory.importanceLow',
  medium: 'memory.importanceMedium',
  high: 'memory.importanceHigh',
  critical: 'memory.importanceCritical',
};

export const OBSERVATION_LABEL_KEY: Record<ObservationKind, string> = {
  observed: 'memory.observed',
  inferred: 'memory.inferred',
};

export const LINK_LABEL_KEY: Record<MemoryLinkType, string> = {
  follows: 'memory.linkFollows',
  relates: 'memory.linkRelates',
  resolves: 'memory.linkResolves',
};

/** Source module → localization label + lucide icon name (resolved in the component). */
export const SOURCE_LABEL_KEY: Record<string, string> = {
  disease: 'memory.sourceDisease',
  growth: 'memory.sourceGrowth',
  weather: 'memory.sourceWeather',
  satellite: 'memory.sourceSatellite',
  soil: 'memory.sourceSoil',
  nutrient: 'memory.sourceNutrient',
  schemes: 'memory.sourceSchemes',
  market: 'memory.sourceMarket',
  experts: 'memory.sourceExperts',
  ai_chat: 'memory.sourceAiChat',
  produce: 'memory.sourceProduce',
  calendar: 'memory.sourceCalendar',
};

/** The source modules offered as timeline filters, in display order. */
export const FILTERABLE_SOURCES: string[] = [
  'disease',
  'nutrient',
  'soil',
  'satellite',
  'growth',
  'weather',
  'produce',
  'experts',
  'schemes',
  'market',
  'ai_chat',
];

export const SEASON_LABEL_KEY: Record<string, string> = {
  kharif: 'memory.seasonKharif',
  rabi: 'memory.seasonRabi',
  summer: 'memory.seasonSummer',
  unknown: 'memory.seasonUnknown',
};
