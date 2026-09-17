jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn() } }));
jest.mock('../services/produceStorage', () => ({
  listCacheKey: jest.fn(() => 'cache-key'),
  produceStorage: { getCachedList: jest.fn(() => []), cacheList: jest.fn() },
}));

import { api } from '@/services/apiClient';
import { ApiError } from '@/types';
import { apiProduceProvider } from '../services/apiProduceProvider';

beforeEach(() => jest.clearAllMocks());

const reads = [
  () => apiProduceProvider.list({}),
  () => apiProduceProvider.upcoming(),
  () => apiProduceProvider.history(),
];

test.each([401, 403, 500])('does not hide HTTP %s behind cached listings', async (status) => {
  for (const read of reads) {
    const error = new ApiError({ status, message: 'Failure', errorCode: 'failure' });
    (api.get as jest.Mock).mockRejectedValueOnce(error);
    await expect(read()).rejects.toBe(error);
  }
});

test('labels network fallback responses as cached', async () => {
  for (const read of reads) {
    (api.get as jest.Mock).mockRejectedValueOnce(
      new ApiError({ status: 0, message: 'Offline', errorCode: 'network_error' }),
    );
    await expect(read()).resolves.toMatchObject({ cached: true });
  }
});
