import { uuid } from '@/utils/id';

import type {
  AnalyzeInput,
  NutrientRecommendation,
  NutrientReport,
} from '../types';
import { mockNutrientReport } from './mockNutrient';
import { applyGroundnutNutrientSafety } from './nutrientMapper';
import { NutrientError, type NutrientProvider } from './nutrientProvider';
import { nutrientStorage } from './nutrientStorage';

/**
 * Local, offline Nutrient provider. Produces a deterministic analysis via the client
 * engine mirror and persists it in MMKV, so the flow / history work in dev without a
 * backend. Honest by construction: with no soil/satellite/weather references offline,
 * findings are "possible", never a fabricated "confirmed".
 */
export const localNutrientProvider: NutrientProvider = {
  async analyze(input: AnalyzeInput): Promise<NutrientReport> {
    const report = applyGroundnutNutrientSafety(mockNutrientReport(input, uuid()));
    nutrientStorage.addLocalReport(input.farmId, report);
    return report;
  },

  async history(farmId: string): Promise<NutrientReport[]> {
    return nutrientStorage
      .localReports(farmId)
      .slice()
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  },

  async latest(farmId: string): Promise<NutrientReport | null> {
    return nutrientStorage.localReports(farmId)[0] ?? null;
  },

  async recommendations(farmId: string): Promise<NutrientRecommendation[]> {
    return nutrientStorage.localReports(farmId)[0]?.recommendations ?? [];
  },

  async getReport(id: string): Promise<NutrientReport> {
    const report = nutrientStorage.getLocalReport(id);
    if (!report) throw new NutrientError('not_found', 'Report not found');
    return report;
  },
};
