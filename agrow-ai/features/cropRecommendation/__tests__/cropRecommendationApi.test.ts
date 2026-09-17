jest.mock('@/config/internalTestFlags', () => ({
  internalTestFlags: { internalFeatureTesting: true },
}));
jest.mock('@/services/apiClient', () => ({ httpClient: { post: jest.fn() } }));

import { httpClient } from '@/services/apiClient';
import { recommendCrop } from '../cropRecommendationApi';

const input = { nitrogen: 90, phosphorus: 42, potassium: 43, temperature_c: 20.9, humidity_percent: 82, ph: 6.5, rainfall_mm: 203 };

test('returns only a valid controlled-test response', async () => {
  (httpClient.post as jest.Mock).mockResolvedValue({ data: {
    status: 'provisional_controlled_test', recommended_crop: 'rice', model_probability: 0.99,
    alternatives: [], validation_status: 'NO_INDEPENDENT_AGROWAI_EVALUATION',
    test_mode: true, general_farmer_release_authorized: false, disclaimer: 'test',
  } });
  await expect(recommendCrop(input)).resolves.toMatchObject({ recommended_crop: 'rice' });
});

test('fails closed when release or probability invariants are invalid', async () => {
  (httpClient.post as jest.Mock).mockResolvedValue({ data: {
    status: 'provisional_controlled_test', recommended_crop: 'rice', model_probability: Number.NaN,
    alternatives: [], validation_status: 'NO_INDEPENDENT_AGROWAI_EVALUATION',
    test_mode: true, general_farmer_release_authorized: false, disclaimer: 'test',
  } });
  await expect(recommendCrop(input)).rejects.toThrow('CROP_RECOMMENDATION_SAFETY_CONTRACT_INVALID');
});
