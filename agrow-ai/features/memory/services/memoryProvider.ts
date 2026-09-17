import { isBackendConfigured } from '@/config/env';
import { logger } from '@/lib/logger';

import type {
  FarmMemory,
  MemoryDashboard,
  MemoryHistoryFilter,
  MemoryRebuildResult,
  MemorySummaryBundle,
  Paginated,
} from '../types';

/**
 * Farm Memory data source contract. Backed by the AgrowAI memory API (aggregation
 * over every module + the deterministic engine) when a backend is configured,
 * otherwise a local offline provider that runs a faithful client mirror of the engine
 * over MMKV. Future embeddings / vector search / RAG / additional AI providers join
 * behind this seam with no frontend change. Missing history is never fabricated.
 */
export interface MemoryProvider {
  dashboard(farmId: string): Promise<MemoryDashboard>;
  latest(farmId: string): Promise<FarmMemory>;
  history(
    farmId: string,
    filter?: MemoryHistoryFilter,
    page?: number,
    pageSize?: number,
  ): Promise<Paginated<FarmMemory>>;
  summary(farmId: string): Promise<MemorySummaryBundle>;
  getMemory(id: string): Promise<FarmMemory>;
  rebuild(farmId: string): Promise<MemoryRebuildResult>;
}

export class MemoryError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'MemoryError';
  }
}

let provider: MemoryProvider | null = null;

export function getMemoryProvider(): MemoryProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require('./apiMemoryProvider').apiMemoryProvider as MemoryProvider;
    logger.info('memory', 'using api provider');
  } else {
    provider = require('./localMemoryProvider').localMemoryProvider as MemoryProvider;
    logger.info('memory', 'using local provider');
  }
  return provider;
}

/** Test seam: force a provider (used to reset between tests). */
export function _setMemoryProvider(next: MemoryProvider | null): void {
  provider = next;
}
