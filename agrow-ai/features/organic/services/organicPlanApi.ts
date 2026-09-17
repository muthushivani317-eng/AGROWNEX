import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import type { ApiOrganicPlanBundle, OrganicPlanBundle } from '../integrationTypes';
import { apiToOrganicPlanBundle } from './organicPlanMapper';

/** Farm-wide adapter. Backend owns agronomy; the client never fabricates actions or rates. */
export async function getOrganicPlanBundle(farmId: string): Promise<OrganicPlanBundle> {
  return apiToOrganicPlanBundle(await api.get<ApiOrganicPlanBundle>(endpoints.organic.plan(farmId)));
}
