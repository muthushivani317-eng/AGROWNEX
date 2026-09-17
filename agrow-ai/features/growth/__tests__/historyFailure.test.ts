jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn() } }));
jest.mock('../services/growthStorage', () => ({ growthStorage: {
  cacheImages: jest.fn(), allImages: jest.fn(() => [{ farmId: 'other-farm' }]),
  imagesForSession: jest.fn(() => []),
} }));

import { api } from '@/services/apiClient';
import { ApiError } from '@/types';
import { apiGrowthProvider } from '../services/apiGrowthProvider';
import { growthStorage } from '../services/growthStorage';

beforeEach(() => jest.clearAllMocks());

it.each([0, 401, 403, 500])('surfaces history failure %s without a false empty or cross-farm response', async (status) => {
  const error = new ApiError({ status, message: 'Failure', errorCode: 'failure' });
  (api.get as jest.Mock).mockRejectedValueOnce(error);
  await expect(apiGrowthProvider.history(null, 'selected-farm')).rejects.toBe(error);
  expect(growthStorage.allImages).not.toHaveBeenCalled();
  expect(growthStorage.cacheImages).not.toHaveBeenCalled();
});

it('returns a genuine empty success and preserves the farm filter', async () => {
  (api.get as jest.Mock).mockResolvedValueOnce({ items: [] });
  await expect(apiGrowthProvider.history(null, 'selected-farm')).resolves.toEqual([]);
  expect(api.get).toHaveBeenCalledWith(expect.any(String), {
    params: { page: 1, page_size: 50, session_id: undefined, farm_id: 'selected-farm' },
  });
});
