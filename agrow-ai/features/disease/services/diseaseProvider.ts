import { isBackendConfigured } from '@/config/env';
import { logger } from '@/lib/logger';

import type { DiseaseReport, DiseaseReportSummary } from '../types';

/**
 * Disease report data source contract. Diagnosis runs through the dedicated
 * crop-specific workflows; this provider owns shared history reads and deletes.
 */
export interface DiseaseProvider {
  listReports(
    farmId?: string | null,
    unassignedOnly?: boolean,
  ): Promise<DiseaseReportSummary[]>;
  getReport(id: string): Promise<DiseaseReport>;
  deleteReport(id: string): Promise<void>;
}

export class DiseaseError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'DiseaseError';
  }
}

let provider: DiseaseProvider | null = null;

export function getDiseaseProvider(): DiseaseProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require('./apiDiseaseProvider').apiDiseaseProvider as DiseaseProvider;
    logger.info('disease', 'using api provider');
  } else {
    provider = require('./localDiseaseProvider').localDiseaseProvider as DiseaseProvider;
    logger.info('disease', 'using local provider');
  }
  return provider;
}
