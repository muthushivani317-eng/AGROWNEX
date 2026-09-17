jest.mock('@/services/apiClient', () => ({ httpClient: { post: jest.fn() } }));

import { httpClient } from '@/services/apiClient';
import { identifyCropInternalOnly } from '../internalSixClassApi';
import { ApiError } from '@/types';

const identified = {
  status: 'identified', identified_crop: 'banana', confidence: 0.91, margin: 0.72,
  calibrated_probabilities: { banana: 0.91, paddy: 0.09 },
  farmer_confirmation_required: true, reason_code: 'CROP_MATCH', scope: 'INTERNAL_ONLY',
  official_accuracy_claim: false, general_farmer_release: 'BLOCKED', request_id: 'request-1',
  image_sha256: 'a'.repeat(64), expires_at: '2026-08-13T01:00:00Z', confirmation_token: 'token',
  suggested_crop: 'banana', suggested_crop_display_ta: 'வாழை',
};

test.each([
  ['missing confidence', { confidence: undefined }],
  ['null identified confidence', { confidence: null }],
  ['NaN confidence', { confidence: Number.NaN }],
  ['infinite margin', { margin: Number.POSITIVE_INFINITY }],
])('fails safely to uncertain for %s', async (_label, invalid) => {
  (httpClient.post as jest.Mock).mockResolvedValueOnce({ data: { ...identified, ...invalid } });
  const result = await identifyCropInternalOnly({ uri: 'file://crop.jpg', mimeType: 'image/jpeg' });
  expect(result).toMatchObject({
    status: 'uncertain', identified_crop: null, suggested_crop: null,
    confidence: null, margin: 0, calibrated_probabilities: {},
    reason_code: 'CROP_IDENTITY_UNCERTAIN',
  });
});

test('preserves valid finite confidence values', async () => {
  (httpClient.post as jest.Mock).mockResolvedValueOnce({ data: identified });
  const result = await identifyCropInternalOnly({ uri: 'file://crop.jpg', mimeType: 'image/jpeg' });
  expect(result.status).toBe('identified');
  expect(result.confidence).toBe(0.91);
  expect(result.margin).toBe(0.72);
});

test.each([
  ['TESTER_ROLE_REQUIRED', 403],
  ['AUTHORIZATION_UNAVAILABLE', 403],
  ['RUNTIME_INTEGRITY_FAILURE', 503],
  ['IMAGE_FORMAT_UNSUPPORTED', 415],
  ['LOW_QUALITY_IMAGE', 422],
] as const)('preserves actionable backend error %s', async (errorCode, status) => {
  (httpClient.post as jest.Mock).mockRejectedValueOnce(
    new ApiError({ status, errorCode, message: errorCode }),
  );
  await expect(identifyCropInternalOnly({ uri: 'file://crop.jpg', mimeType: 'image/jpeg' }))
    .rejects.toMatchObject({ errorCode, status });
});

test('preserves a structured non-Axios error instead of relabeling it', async () => {
  const error = { status: 422, errorCode: 'CROP_CONFIRMATION_EXPIRED', message: 'expired' };
  (httpClient.post as jest.Mock).mockRejectedValueOnce(error);
  await expect(identifyCropInternalOnly({ uri: 'file://crop.jpg', mimeType: 'image/jpeg' }))
    .rejects.toBe(error);
});
