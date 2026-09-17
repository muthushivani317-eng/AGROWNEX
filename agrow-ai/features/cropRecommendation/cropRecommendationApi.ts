import { internalTestFlags } from '@/config/internalTestFlags';
import { httpClient } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

export interface CropRecommendationInput {
  nitrogen: number;
  phosphorus: number;
  potassium: number;
  temperature_c: number;
  humidity_percent: number;
  ph: number;
  rainfall_mm: number;
}

export interface CropRecommendationResult {
  status: 'provisional_controlled_test';
  recommended_crop: string;
  model_probability: number;
  alternatives: Array<{ crop: string; model_probability: number }>;
  validation_status: 'NO_INDEPENDENT_AGROWAI_EVALUATION';
  test_mode: true;
  general_farmer_release_authorized: false;
  disclaimer: string;
}

export async function recommendCrop(
  input: CropRecommendationInput,
): Promise<CropRecommendationResult> {
  if (!internalTestFlags.internalFeatureTesting) {
    throw new Error('CONTROLLED_TEST_BUILD_REQUIRED');
  }
  const response = await httpClient.post<CropRecommendationResult>(
    endpoints.cropRecommendation.predict,
    input,
  );
  const result = response.data;
  if (
    result.test_mode !== true ||
    result.general_farmer_release_authorized !== false ||
    result.status !== 'provisional_controlled_test' ||
    !Number.isFinite(result.model_probability)
  ) {
    throw new Error('CROP_RECOMMENDATION_SAFETY_CONTRACT_INVALID');
  }
  return result;
}
