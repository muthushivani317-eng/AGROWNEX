import type { OrganicFarmMode, OrganicPracticeType } from './types';

export const ORGANIC_PROFILE_CACHE = 'agrowai.organic.profile';
export const ORGANIC_PRACTICE_CACHE = 'agrowai.organic.practices';
export const ORGANIC_OUTBOX = 'agrowai.organic.outbox';
export const organicKeys = {
  all: ['organic'] as const,
  profile: (farmId: string) => ['organic', 'profile', farmId] as const,
  practices: (farmId: string) => ['organic', 'practices', farmId] as const,
};
export const ORGANIC_MODES: OrganicFarmMode[] = ['conventional', 'organic_preferred', 'transitioning', 'fully_organic'];
export const PRACTICE_TYPES: OrganicPracticeType[] = ['amendment', 'seed_treatment', 'biological_treatment', 'botanical_spray', 'trap', 'mechanical_weeding', 'mulching', 'green_manure', 'crop_rotation', 'irrigation_drainage', 'scouting', 'harvest', 'custom'];
