import { httpClient } from '@/services/apiClient';

import type { DiseaseRecommendation } from '../components/RecommendationResultCard';

type LookupResponse = DiseaseRecommendation & { outcome: 'RECOMMENDATION_PARTIAL' | 'RECOMMENDATION_NOT_VERIFIED' };

/** Registry-only lookup; callers must invoke this solely after accepted crop-confirmed diagnosis. */
export async function loadDiseaseRecommendation(cropId: string, runtimeLabel: string): Promise<LookupResponse | null> {
  return loadRecommendation('/disease-recommendations/lookup', cropId, runtimeLabel);
}

export async function loadRestrictedDiseaseRecommendation(
  cropId: 'chilli' | 'redgram',
  runtimeLabel: string,
): Promise<LookupResponse | null> {
  return loadRecommendation('/disease-recommendations/lookup-restricted', cropId, runtimeLabel);
}

async function loadRecommendation(
  endpoint: string,
  cropId: string,
  runtimeLabel: string,
): Promise<LookupResponse | null> {
  const response = await httpClient.post<unknown>(endpoint, {
    crop_id: cropId,
    runtime_label: runtimeLabel,
    diagnosis_accepted: true,
    crop_confirmed: true,
  });
  const body = response.data as Partial<LookupResponse>;
  return body.outcome === 'RECOMMENDATION_PARTIAL' && typeof body.canonical_disease_name_ta === 'string'
    ? body as LookupResponse
    : null;
}
