jest.mock('@/services/apiClient', () => ({ httpClient: { post: jest.fn() } }));
import { httpClient } from '@/services/apiClient';
import { identifyPlant } from '../plantIdentifierApi';

test('Plant Identifier stays on its separate endpoint', async () => {
  (httpClient.post as jest.Mock).mockResolvedValueOnce({
    data: {
      request_id: 'request-1', status: 'uncertain', common_name: null,
      scientific_name: null, family: null, description: null,
      visible_characteristics: [], possible_alternatives: [], confidence: 0.2,
      informational_only: true, used_for_disease_routing: false,
      disease_inference_available: false, crop_confirmation_created: false,
      provider: 'gemini', language: 'ta', disclaimer: 'Informational only',
      processing_status: 'complete', error_code: 'PLANT_IDENTIFIER_UNCERTAIN',
      retry_allowed: true,
    },
  });
  const result = await identifyPlant({ uri: 'file://plant.jpg', mimeType: 'image/jpeg' });
  expect(httpClient.post).toHaveBeenCalledWith(
    '/plant-identifier/identify', expect.any(FormData), expect.any(Object),
  );
  expect(result.status).toBe('uncertain');
  expect(result.used_for_disease_routing).toBe(false);
  expect(result.disease_inference_available).toBe(false);
});

test('rejects any backend response that could route disease or confirm a crop', async () => {
  (httpClient.post as jest.Mock).mockResolvedValueOnce({
    data: {
      informational_only: true, used_for_disease_routing: true,
      disease_inference_available: false, crop_confirmation_created: false,
    },
  });
  await expect(identifyPlant({ uri: 'file://plant.jpg', mimeType: 'image/jpeg' }))
    .rejects.toThrow('PLANT_IDENTIFIER_ROUTING_INVARIANT_VIOLATION');
});
