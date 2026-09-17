import { isBackendConfigured } from '@/config/env';
import type { OrganicFarmProfile, OrganicFarmProfileInput, OrganicPractice, OrganicPracticeInput } from '../types';

export interface OrganicProvider {
  getProfile(farmId: string): Promise<OrganicFarmProfile | null>;
  saveProfile(farmId: string, input: OrganicFarmProfileInput, idempotencyKey?: string): Promise<OrganicFarmProfile>;
  listPractices(farmId: string): Promise<OrganicPractice[]>;
  createPractice(input: OrganicPracticeInput): Promise<OrganicPractice>;
}
let provider: OrganicProvider | null = null;
export function getOrganicProvider(): OrganicProvider {
  if (provider) return provider;
  provider = isBackendConfigured
    ? require('./apiOrganicProvider').apiOrganicProvider as OrganicProvider
    : require('./localOrganicProvider').localOrganicProvider as OrganicProvider;
  return provider;
}
