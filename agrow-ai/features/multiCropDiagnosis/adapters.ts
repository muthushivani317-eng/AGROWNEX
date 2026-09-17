import { normalizeCropId } from '@/config/cropCapabilities';
import type { AxiosRequestConfig } from 'axios';
import { httpClient } from '@/services/apiClient';

import {
  classifyCropDiagnosisFailure,
  parseCropDiagnosisResponse,
  parseRestrictedCropDiagnosisResponse,
} from './responseParser';
import type { CropDiagnosisAdapter, CropDiagnosisResult, ModelNotAvailableResult } from './types';
import type { ResolvedDiseaseCapability } from './cropRegistry';

const RESTRICTED = new Set(['chilli', 'redgram']);
const JOINT_ROUTES: Readonly<Record<string, string>> = {
  rice: 'paddy',
  cotton: 'cotton',
  groundnut: 'groundnut',
};
const noRetry = { _skipRetry: true } as AxiosRequestConfig;

export function unavailableAdapter(crop: string): CropDiagnosisAdapter {
  const cropId = normalizeCropId(crop);
  return {
    cropId,
    status: 'NOT_AVAILABLE',
    async predict(): Promise<ModelNotAvailableResult> {
      return { status: 'model_not_available', code: 'MODEL_NOT_AVAILABLE', cropId, diagnosis: null };
    },
  };
}

export function cropDiagnosisAdapter(
  crop: string,
  capability?: ResolvedDiseaseCapability | null,
): CropDiagnosisAdapter {
  const cropId = normalizeCropId(crop);
  if (!capability || !capability.selectable || capability.cropId !== cropId) {
    return unavailableAdapter(cropId);
  }
  if (capability.predictionKind === 'restricted' && RESTRICTED.has(cropId)) {
    return {
      cropId,
      status: 'RESTRICTED_INTERNAL_TESTING_ONLY',
      async predict(input): Promise<CropDiagnosisResult> {
        if (input.cropConfirmed !== true) throw new Error('USER_CROP_CONFIRMATION_REQUIRED');
        if (!input.cropConfirmationToken) throw new Error('CROP_CONFIRMATION_REQUIRED');
        const form = new FormData();
        form.append('image', {
          uri: input.uri,
          type: input.mimeType,
          name: `${cropId}-${Date.now()}.jpg`,
        } as unknown as Blob);
        form.append('crop_confirmation_token', input.cropConfirmationToken);
        if (input.farmId) form.append('farm_id', input.farmId);
        if (input.kvkSession) form.append('kvk_session', 'true');
        if (input.kvkSession && input.reviewConsent !== undefined) {
          form.append('review_consent', String(input.reviewConsent));
        }
        try {
          const response = await httpClient.post<unknown>(
            `/disease/${cropId}/predict-restricted`,
            form,
            { ...noRetry },
          );
          return parseRestrictedCropDiagnosisResponse(
            response.data,
            cropId,
            capability.supportedClassIds,
          );
        } catch (error) {
          return classifyCropDiagnosisFailure(error);
        }
      },
    };
  }
  const routeCrop = JOINT_ROUTES[cropId];
  if (!routeCrop || capability.predictionKind !== 'legacy_joint') return unavailableAdapter(cropId);
  return {
    cropId,
    status: 'LEGACY_JOINT_MODEL_AUDIT_REQUIRED',
    async predict(input): Promise<CropDiagnosisResult> {
      if (input.cropConfirmed !== true) throw new Error('USER_CROP_CONFIRMATION_REQUIRED');
      if (!input.cropConfirmationToken) throw new Error('CROP_CONFIRMATION_REQUIRED');
      const form = new FormData();
      form.append('image', {
        uri: input.uri,
        type: input.mimeType,
        name: `${routeCrop}-${Date.now()}.jpg`,
      } as unknown as Blob);
      form.append('crop_confirmed', 'true');
      form.append('crop_confirmation_token', input.cropConfirmationToken);
      if (input.farmId) form.append('farm_id', input.farmId);
      try {
        const response = await httpClient.post<unknown>(
          `/disease/${routeCrop}/predict`,
          form,
          { ...noRetry },
        );
        return parseCropDiagnosisResponse(
          response.data,
          cropId,
          capability.supportedClassIds,
        );
      } catch (error) {
        return classifyCropDiagnosisFailure(error);
      }
    },
  };
}

export async function submitCropDiagnosisFeedback(
  crop: string,
  payload: {
    request_id: string;
    outcome_helpful: boolean;
    corrected_class_id?: string;
    notes?: string;
  },
): Promise<void> {
  const cropId = normalizeCropId(crop);
  const routeCrop = JOINT_ROUTES[cropId];
  if (!routeCrop) throw new Error('UNSUPPORTED_CROP_ADAPTER');
  await httpClient.post(`/disease/${routeCrop}/feedback`, payload, noRetry);
}

export function mayCallPredictionEndpoint(
  crop: string,
  capability?: ResolvedDiseaseCapability | null,
): boolean {
  return capability?.selectable === true && capability.cropId === normalizeCropId(crop);
}
