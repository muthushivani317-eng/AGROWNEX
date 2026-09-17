import type { AxiosRequestConfig } from 'axios';
import { httpClient } from '@/services/apiClient';
import type { BananaFeedbackRequest, BananaPredictionResponse } from './types';

type UploadImage = { uri: string; mimeType: string; name?: string };
const noRetry = { _skipRetry: true } as AxiosRequestConfig;

export async function predictBanana(
  image: UploadImage,
  cropConfirmationToken: string,
  farmId?: string,
): Promise<BananaPredictionResponse> {
  const form = new FormData();
  form.append('image', {
    uri: image.uri,
    type: image.mimeType,
    name: image.name ?? `banana-${Date.now()}.jpg`,
  } as unknown as Blob);
  form.append('crop_confirmation_token', cropConfirmationToken);
  if (farmId) form.append('farm_id', farmId);
  const response = await httpClient.post<BananaPredictionResponse>(
    '/disease/banana/predict',
    form,
    { ...noRetry },
  );
  return response.data;
}

export async function submitBananaFeedback(payload: BananaFeedbackRequest): Promise<void> {
  await httpClient.post('/disease/banana/feedback', payload, noRetry);
}
