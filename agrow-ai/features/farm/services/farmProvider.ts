import { isBackendConfigured } from '@/config/env';
import { logger } from '@/lib/logger';

import type {
  BoundaryInput,
  Farm,
  FarmBoundary,
  FarmImage,
  FarmImageInput,
  FarmInput,
  FarmListParams,
  FarmListResult,
} from '../types';

/**
 * Farm data source contract, implemented by the backend provider and an
 * offline-first local provider — selected at runtime, so hooks/screens depend
 * only on this interface (mirrors the swappable auth/profile providers).
 */
export interface FarmProvider {
  list(params: FarmListParams): Promise<FarmListResult>;
  get(id: string): Promise<Farm>;
  create(input: FarmInput): Promise<Farm>;
  update(id: string, input: FarmInput): Promise<Farm>;
  remove(id: string): Promise<void>;
  getBoundary(id: string): Promise<FarmBoundary | null>;
  updateBoundary(id: string, input: BoundaryInput): Promise<FarmBoundary>;
  listImages(id: string): Promise<FarmImage[]>;
  addImage(id: string, media: FarmImageInput): Promise<FarmImage>;
}

export class FarmError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'FarmError';
  }
}

let provider: FarmProvider | null = null;

export function getFarmProvider(): FarmProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require('./apiFarmProvider').apiFarmProvider as FarmProvider;
    logger.info('farm', 'using api provider');
  } else {
    provider = require('./localFarmProvider').localFarmProvider as FarmProvider;
    logger.info('farm', 'using local provider');
  }
  return provider;
}
