import { isBackendConfigured } from '@/config/env';
import { logger } from '@/lib/logger';

import type { FarmerPreferences, FarmerProfile, FarmerProfileInput } from '../types';

/**
 * Profile data source contract. Implemented by both the real backend provider
 * and a local, offline-first provider — selected at runtime, so screens and
 * hooks depend only on this interface (mirrors the swappable auth provider).
 */
export interface ProfileProvider {
  getProfile(): Promise<FarmerProfile>;
  updateProfile(input: FarmerProfileInput): Promise<FarmerProfile>;
  getPreferences(): Promise<FarmerPreferences>;
  updatePreferences(patch: Partial<FarmerPreferences>): Promise<FarmerPreferences>;
}

export class ProfileError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'ProfileError';
  }
}

// Lazily resolved so env/config is read once and the choice is logged.
let provider: ProfileProvider | null = null;

export function getProfileProvider(): ProfileProvider {
  if (provider) return provider;
  // Deferred requires avoid loading the axios-based provider in local mode.
  if (isBackendConfigured) {
    provider = require('./apiProfileProvider').apiProfileProvider as ProfileProvider;
    logger.info('profile', 'using api provider');
  } else {
    provider = require('./localProfileProvider').localProfileProvider as ProfileProvider;
    logger.info('profile', 'using local provider');
  }
  return provider;
}
