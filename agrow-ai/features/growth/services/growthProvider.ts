import { isBackendConfigured } from '@/config/env';
import { logger } from '@/lib/logger';

import type {
  GrowthImage,
  GrowthSessionDetail,
  GrowthTimeline,
  UploadGrowthInput,
  UploadResult,
} from '../types';

/**
 * Crop Growth data source contract. Backed by the AgrowAI growth API (Gemini
 * vision + R2) when configured, otherwise a local, offline provider with a
 * deterministic mock analysis (mirrors the app's other swappable providers).
 * Designed so a future model (YOLO, nutrient, pest, growth-stage) can replace
 * Gemini with no frontend change.
 */
export interface GrowthProvider {
  upload(input: UploadGrowthInput): Promise<UploadResult>;
  history(sessionId?: string | null, farmId?: string | null): Promise<GrowthImage[]>;
  timeline(sessionId?: string | null, farmId?: string | null): Promise<GrowthTimeline>;
  latest(): Promise<GrowthImage | null>;
  session(id: string): Promise<GrowthSessionDetail>;
  deleteImage(id: string): Promise<void>;
}

export class GrowthError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'GrowthError';
  }
}

let provider: GrowthProvider | null = null;

export function getGrowthProvider(): GrowthProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require('./apiGrowthProvider').apiGrowthProvider as GrowthProvider;
    logger.info('growth', 'using api provider');
  } else {
    provider = require('./localGrowthProvider').localGrowthProvider as GrowthProvider;
    logger.info('growth', 'using local provider');
  }
  return provider;
}
