jest.mock('@/services/apiClient', () => ({ api: { post: jest.fn() } }));

import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

import { analyzeLcc } from '../api';

test('sends a farm-scoped image to the dedicated LCC endpoint', async () => {
  const response = { panel_number: 4, nitrogen_status: 'borderline' };
  (api.post as jest.Mock).mockResolvedValue(response);

  await expect(
    analyzeLcc({
      farmId: 'farm-1',
      imageBase64: 'base64-image',
      mimeType: 'image/jpeg',
    }),
  ).resolves.toBe(response);

  expect(api.post).toHaveBeenCalledWith(
    endpoints.lcc.analyze,
    {
      farm_id: 'farm-1',
      image_base64: 'base64-image',
      mime_type: 'image/jpeg',
    },
    expect.objectContaining({ _skipRetry: true }),
  );
});
