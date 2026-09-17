import type { AxiosRequestConfig } from 'axios';
import { httpClient } from '@/services/apiClient';
export interface PlantIdentificationResult {
  request_id: string;
  status: 'identified' | 'uncertain' | 'non_plant' | 'invalid_image' | 'provider_error';
  common_name: string | null;
  scientific_name: string | null;
  family: string | null;
  description: string | null;
  visible_characteristics: string[];
  possible_alternatives: Array<{
    common_name: string;
    scientific_name: string | null;
    confidence: number;
  }>;
  confidence: number;
  informational_only: true;
  used_for_disease_routing: false;
  disease_inference_available: false;
  crop_confirmation_created: false;
  provider: 'gemini';
  language: 'ta' | 'en';
  disclaimer: string;
  processing_status: 'complete' | 'rejected' | 'failed';
  error_code: string | null;
  retry_allowed: boolean;
}
const noRetry = { _skipRetry: true } as AxiosRequestConfig;
export async function identifyPlant(input: {
  uri: string;
  mimeType: string;
  preferredLanguage?: 'ta' | 'en';
  userNote?: string;
}): Promise<PlantIdentificationResult> {
  const form = new FormData();
  form.append('image', { uri: input.uri, type: input.mimeType, name: `plant-identification-${Date.now()}.jpg` } as unknown as Blob);
  form.append('preferred_language', input.preferredLanguage ?? 'ta');
  if (input.userNote?.trim()) form.append('user_note', input.userNote.trim());
  const response = await httpClient.post<PlantIdentificationResult>(
    '/plant-identifier/identify', form,
    { ...noRetry },
  );
  const result = response.data;
  if (
    result.informational_only !== true ||
    result.used_for_disease_routing !== false ||
    result.disease_inference_available !== false ||
    result.crop_confirmation_created !== false
  ) {
    throw new Error('PLANT_IDENTIFIER_ROUTING_INVARIANT_VIOLATION');
  }
  return result;
}
