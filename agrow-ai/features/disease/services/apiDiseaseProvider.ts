import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import type { Paginated } from '@/types';

import type {
  ApiDiseaseReport,
  ApiDiseaseReportSummary,
  DiseaseReport,
  DiseaseReportSummary,
} from '../types';
import { apiToReport, apiToSummary } from './diseaseMapper';
import type { DiseaseProvider } from './diseaseProvider';

/**
 * Backend disease report provider (docs/API_CONTRACT.md → DISEASE).
 */
export const apiDiseaseProvider: DiseaseProvider = {
  async listReports(
    farmId?: string | null,
    unassignedOnly = false,
  ): Promise<DiseaseReportSummary[]> {
    const data = await api.get<Paginated<ApiDiseaseReportSummary>>(
      endpoints.disease.history,
      {
        params: {
          page: 1,
          page_size: 50,
          farm_id: farmId ?? undefined,
          unassigned_only: unassignedOnly || undefined,
        },
      },
    );
    return data.items.map(apiToSummary);
  },

  async getReport(id: string): Promise<DiseaseReport> {
    return apiToReport(await api.get<ApiDiseaseReport>(endpoints.disease.byId(id)));
  },

  async deleteReport(id: string): Promise<void> {
    await api.delete<null>(endpoints.disease.byId(id));
  },
};
