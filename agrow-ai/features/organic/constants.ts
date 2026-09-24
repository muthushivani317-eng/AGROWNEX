import type { OrganicFarmMode, OrganicPracticeType } from './types';

export const ORGANIC_PROFILE_CACHE = 'agrowai.organic.profile';
export const ORGANIC_PRACTICE_CACHE = 'agrowai.organic.practices';
export const ORGANIC_OUTBOX = 'agrowai.organic.outbox';
export const organicKeys = {
  all: ['organic'] as const,
  profile: (farmId: string) => ['organic', 'profile', farmId] as const,
  practices: (farmId: string) => ['organic', 'practices', farmId] as const,
  readinessQuestions: ['organic', 'readiness', 'questions'] as const,
  readinessHistory: (farmId: string) => ['organic', 'readiness', 'history', farmId] as const,
  plots: (farmId: string) => ['organic', 'plots', farmId] as const,
  cropCycles: (plotId: string) => ['organic', 'cropCycles', plotId] as const,
  cropCyclePlan: (cycleId: string) => ['organic', 'cropCyclePlan', cycleId] as const,
  todayTask: (farmId: string) => ['organic', 'todayTask', farmId] as const,
  pgsStatus: (farmId: string) => ['organic', 'pgs', 'status', farmId] as const,
  pgsPeerAssignments: ['organic', 'pgs', 'peerAssignments'] as const,
};
export const ORGANIC_MODES: OrganicFarmMode[] = ['conventional', 'organic_preferred', 'transitioning', 'fully_organic'];
export const PRACTICE_TYPES: OrganicPracticeType[] = ['amendment', 'seed_treatment', 'biological_treatment', 'botanical_spray', 'trap', 'mechanical_weeding', 'mulching', 'green_manure', 'crop_rotation', 'irrigation_drainage', 'scouting', 'harvest', 'custom'];
