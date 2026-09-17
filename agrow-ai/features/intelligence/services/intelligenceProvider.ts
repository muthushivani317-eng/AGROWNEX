import { isBackendConfigured } from '@/config/env';
import { logger } from '@/lib/logger';

import type {
  IntelligenceDashboard,
  IntelligenceHistoryEntry,
  IntelligenceReport,
  Paginated,
} from '../types';

/**
 * Crop Intelligence data source contract. Backed by the AgrowAI intelligence API
 * (aggregation over every module + the pure engine) when a backend is configured,
 * otherwise a local offline provider that runs a faithful client mirror of the engine
 * over MMKV. Future reasoning sources (LLM synthesis, AI Memory) join behind this seam
 * with no frontend change. A missing module lowers confidence — it is never fabricated.
 */
export interface IntelligenceProvider {
  dashboard(farmId: string): Promise<IntelligenceDashboard>;
  latest(farmId: string): Promise<IntelligenceReport>;
  history(
    farmId: string,
    page?: number,
    pageSize?: number,
  ): Promise<Paginated<IntelligenceHistoryEntry>>;
  getReport(id: string): Promise<IntelligenceReport>;
  refresh(farmId: string): Promise<IntelligenceReport>;
}

export class IntelligenceError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'IntelligenceError';
  }
}

let provider: IntelligenceProvider | null = null;

export function getIntelligenceProvider(): IntelligenceProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require('./apiIntelligenceProvider').apiIntelligenceProvider as IntelligenceProvider;
    logger.info('intelligence', 'using api provider');
  } else {
    provider = require('./localIntelligenceProvider')
      .localIntelligenceProvider as IntelligenceProvider;
    logger.info('intelligence', 'using local provider');
  }
  return provider;
}

/** Test seam: force a provider (used to reset between tests). */
export function _setIntelligenceProvider(next: IntelligenceProvider | null): void {
  provider = next;
}
