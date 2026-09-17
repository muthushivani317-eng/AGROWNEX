jest.mock('@/services/apiClient', () => ({ httpClient: { post: jest.fn() } }));

import { httpClient } from '@/services/apiClient';
import { cropDiagnosisAdapter, mayCallPredictionEndpoint, unavailableAdapter } from '../adapters';
import type { ResolvedDiseaseCapability } from '../cropRegistry';

const authorizedRice: ResolvedDiseaseCapability = {
  cropId: 'rice', visible: true, selectable: true, runtimeReady: true,
  integrityVerified: true, adapterAvailable: true, userAuthorized: true,
  releaseScope: 'internal', fieldValidationStatus: 'IN_PROGRESS',
  supportedClassIds: ['rice_blast'], predictionKind: 'legacy_joint',
};

beforeEach(() => jest.clearAllMocks());

test.each(['blackgram', 'coconut', 'paddy', 'cotton', 'groundnut', 'chilli', 'redgram'])(
  '%s is unavailable until its backend model is authorized',
  async (crop) => {
    const result = await cropDiagnosisAdapter(crop).predict({ uri: 'file://leaf.jpg', mimeType: 'image/jpeg' });
    expect(result).toMatchObject({ status: 'model_not_available', code: 'MODEL_NOT_AVAILABLE', diagnosis: null });
    expect(httpClient.post).not.toHaveBeenCalled();
  },
);

test('no endpoint is callable without a current server-authorized capability', () => {
  expect(mayCallPredictionEndpoint('banana')).toBe(false);
  for (const crop of ['paddy', 'cotton', 'groundnut', 'chilli', 'redgram']) {
    expect(mayCallPredictionEndpoint(crop)).toBe(false);
  }
});

test('an authorized allowlisted capability dispatches to its fixed local route', async () => {
  (httpClient.post as jest.Mock).mockResolvedValueOnce({
    data: { status: 'runtime_not_ready', crop_id: 'rice', message: 'Unavailable.' },
  });
  const result = await cropDiagnosisAdapter('rice', authorizedRice).predict({
    uri: 'file://leaf.jpg', mimeType: 'image/jpeg', cropConfirmed: true,
    cropConfirmationToken: 'token',
  });
  expect(httpClient.post).toHaveBeenCalledWith('/disease/paddy/predict', expect.any(FormData), expect.any(Object));
  expect(result).toMatchObject({ status: 'runtime_not_ready' });
});

test('a mismatched or revoked capability never dispatches', async () => {
  const result = await cropDiagnosisAdapter('rice', { ...authorizedRice, selectable: false }).predict({
    uri: 'file://leaf.jpg', mimeType: 'image/jpeg', cropConfirmed: true,
  });
  expect(result).toMatchObject({ status: 'model_not_available' });
  expect(httpClient.post).not.toHaveBeenCalled();
});

test('explicit unavailable adapter returns a typed result without a request', async () => {
  const result = await unavailableAdapter('maize').predict({ uri: 'unused', mimeType: 'image/jpeg' });
  expect(result).toMatchObject({ cropId: 'maize', status: 'model_not_available' });
  expect(httpClient.post).not.toHaveBeenCalled();
});
