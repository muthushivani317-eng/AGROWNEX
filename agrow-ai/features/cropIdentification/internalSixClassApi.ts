import { isAxiosError, type AxiosRequestConfig } from 'axios';
import { httpClient } from '@/services/apiClient';
import type { SupportedCropId } from './types';

function cropIdentificationRequestError(error: unknown): Error {
  const structured = error as { status?: unknown; errorCode?: unknown };
  if (typeof structured?.status === 'number' && typeof structured?.errorCode === 'string') {
    return error as Error;
  }
  if (isAxiosError(error)) {
    const status = error.response?.status;
    const data = error.response?.data as { error_code?: string; detail?: { code?: string } } | undefined;
    const backendCode = data?.error_code ?? data?.detail?.code;
    if (backendCode) {
      return Object.assign(new Error(backendCode), { status, errorCode: backendCode });
    }
    if (status === 422 || status === 415 || status === 413) return new Error('CROP_IMAGE_REJECTED');
    if (!error.response) return new Error('NETWORK_UNREACHABLE');
    return new Error('SERVER_ERROR');
  }
  return error instanceof Error ? error : new Error('SERVER_ERROR');
}

export type InternalSixClassResult = {
  status: 'identified' | 'uncertain' | 'low_quality';
  identified_crop: SupportedCropId | null;
  confidence: number | null;
  farmer_confirmation_required: true;
  calibrated_probabilities: Record<string, number>;
  margin: number;
  reason_code: 'CROP_MATCH' | 'CROP_IDENTITY_UNCERTAIN';
  scope: 'INTERNAL_ONLY';
  official_accuracy_claim: false;
  general_farmer_release: 'BLOCKED';
  request_id: string;
  image_sha256: string;
  expires_at: string;
  confirmation_token: string;
  suggested_crop: SupportedCropId | null;
  suggested_crop_display_ta: string;
};

export type InternalConfirmationResult = {
  status: 'FARMER_CONFIRMED' | 'FARMER_CORRECTED';
  request_id: string;
  confirmed_crop: SupportedCropId;
  farmer_confirmation_required: true;
  reason_code: 'DISEASE_RUNTIME_RESTRICTED';
  scope: 'INTERNAL_ONLY';
  general_farmer_release: 'BLOCKED';
  confirmation_token: string;
  image_sha256: string;
  expires_at: string;
};

export function normalizeInternalSixClassResult(
  value: InternalSixClassResult,
): InternalSixClassResult {
  const probabilitiesAreFinite = Object.values(
    value.calibrated_probabilities ?? {},
  ).every((probability) => Number.isFinite(probability));
  const confidenceIsFinite =
    typeof value.confidence === 'number' && Number.isFinite(value.confidence);
  const confidenceIsValid =
    confidenceIsFinite ||
    (value.status !== 'identified' && value.confidence === null);
  const marginIsFinite = Number.isFinite(value.margin);

  if (confidenceIsValid && marginIsFinite && probabilitiesAreFinite) {
    return value;
  }

  return {
    ...value,
    status: 'uncertain',
    identified_crop: null,
    suggested_crop: null,
    suggested_crop_display_ta: '',
    confidence: null,
    margin: 0,
    calibrated_probabilities: {},
    reason_code: 'CROP_IDENTITY_UNCERTAIN',
  };
}

export async function identifyCropInternalOnly(input: {
  uri: string;
  mimeType: string;
}): Promise<InternalSixClassResult> {
  const form = new FormData();
  form.append('image', {
    uri: input.uri,
    type: input.mimeType,
    name: 'crop-id-internal.jpg',
  } as unknown as Blob);
  try {
    const response = await httpClient.post<InternalSixClassResult>(
      '/crop-identity-six-class-internal/predict',
      form,
      { _skipRetry: true } as AxiosRequestConfig,
    );
    const value = response.data;
    if (
      value.scope !== 'INTERNAL_ONLY' ||
      value.general_farmer_release !== 'BLOCKED' ||
      value.official_accuracy_claim !== false ||
      value.farmer_confirmation_required !== true
    ) {
      throw new Error('UNSAFE_INTERNAL_CROP_ID_RESPONSE');
    }
    return normalizeInternalSixClassResult(value);
  } catch (error) {
    throw cropIdentificationRequestError(error);
  }
}

export async function confirmInternalCrop(input: {
  requestId: string;
  confirmedCrop: SupportedCropId;
  correction: boolean;
}): Promise<InternalConfirmationResult> {
  const form = new FormData();
  form.append('request_id', input.requestId);
  form.append('confirmed_crop', input.confirmedCrop);
  form.append('correction', String(input.correction));
  let data: InternalConfirmationResult;
  try {
    const response = await httpClient.post<InternalConfirmationResult>(
      '/crop-identity-six-class-internal/confirm',
      form,
      { _skipRetry: true } as AxiosRequestConfig,
    );
    data = response.data;
  } catch (error) {
    const candidate = error as { status?: unknown; errorCode?: unknown };
    if (
      candidate.status === 409 &&
      candidate.errorCode === 'CROP_CONFIRMATION_ALREADY_USED'
    ) {
      throw new Error('CROP_CONFIRMATION_ALREADY_USED');
    }
    throw error;
  }
  if (data.general_farmer_release !== 'BLOCKED') {
    throw new Error('UNSAFE_INTERNAL_CONFIRMATION_RESPONSE');
  }
  return data;
}
