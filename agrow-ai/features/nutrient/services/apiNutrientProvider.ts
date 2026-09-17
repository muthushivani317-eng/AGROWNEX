import type { AxiosRequestConfig } from 'axios';

import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError, type Paginated as ApiPaginated } from '@/types';

import type {
  AnalyzeInput,
  ApiNutrientRecommendation,
  ApiNutrientReport,
  NutrientRecommendation,
  NutrientReport,
} from '../types';
import { apiToRecommendation, apiToReport } from './nutrientMapper';
import type { NutrientProvider } from './nutrientProvider';
import { nutrientStorage } from './nutrientStorage';

// Gemini vision + soil/satellite/weather corroboration + the R2 upload can
// together take longer than the client's default 20s timeout (2026-09-03:
// one real request took 38s). This call gets more room, and never
// auto-retries -- a retry on a slow-but-working attempt resubmits the whole
// image and reruns the full pipeline, compounding the wait and burning the
// daily AI quota faster (the same failure mode fixed for disease/predict
// the same day).
const ANALYZE_TIMEOUT_MS = 45000;
const noRetry = { _skipRetry: true, timeout: ANALYZE_TIMEOUT_MS } as AxiosRequestConfig;

/**
 * Backend Nutrient provider (docs/API_CONTRACT → nutrient). Gemini vision, the
 * corroboration engine and R2 storage run server-side. History / latest / report are
 * mirrored to MMKV so results stay readable offline; on a network error the last
 * cached copy is served. A failed analyze surfaces the error so the hook can queue it.
 */
export const apiNutrientProvider: NutrientProvider = {
  async analyze(input: AnalyzeInput): Promise<NutrientReport> {
    const dto = await api.post<ApiNutrientReport>(
      endpoints.nutrient.analyze,
      {
        image_base64: input.imageBase64,
        mime_type: input.mimeType,
        farm_id: input.farmId,
        crop: input.crop,
        language: input.language,
        capture_method: input.captureMethod,
        latitude: input.latitude,
        longitude: input.longitude,
      },
      { ...noRetry },
    );
    const report = apiToReport(dto);
    nutrientStorage.cacheReport(report);
    return report;
  },

  async history(farmId: string): Promise<NutrientReport[]> {
    try {
      const data = await api.get<ApiPaginated<ApiNutrientReport>>(
        endpoints.nutrient.history,
        { params: { farm_id: farmId, page: 1, page_size: 50 } },
      );
      const items = data.items.map(apiToReport);
      nutrientStorage.cacheHistory(farmId, items);
      return items;
    } catch (err) {
      const cached = nutrientStorage.getCachedHistory(farmId);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      throw err;
    }
  },

  async latest(farmId: string): Promise<NutrientReport | null> {
    try {
      const dto = await api.get<ApiNutrientReport>(endpoints.nutrient.latest, {
        params: { farm_id: farmId },
      });
      const report = apiToReport(dto);
      nutrientStorage.cacheLatest(farmId, report);
      return report;
    } catch (err) {
      if (err instanceof ApiError) {
        // No analysis yet is an honest "empty", not an error.
        if (err.errorCode === 'nutrient_data_unavailable') return null;
        if (err.isNetwork) return nutrientStorage.getCachedLatest(farmId);
      }
      throw err;
    }
  },

  async recommendations(farmId: string): Promise<NutrientRecommendation[]> {
    const dto = await api.get<ApiNutrientRecommendation[]>(
      endpoints.nutrient.recommendations,
      { params: { farm_id: farmId } },
    );
    return dto.map(apiToRecommendation);
  },

  async getReport(id: string): Promise<NutrientReport> {
    try {
      const report = apiToReport(
        await api.get<ApiNutrientReport>(endpoints.nutrient.report(id)),
      );
      nutrientStorage.cacheReport(report);
      return report;
    } catch (err) {
      const cached = nutrientStorage.getCachedReport(id);
      if (cached && err instanceof ApiError && err.isNetwork) return cached;
      throw err;
    }
  },
};
