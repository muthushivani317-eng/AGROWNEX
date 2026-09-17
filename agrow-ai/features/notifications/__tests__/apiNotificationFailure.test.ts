jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn() } }));
jest.mock('../services/notificationStorage', () => ({
  listCacheKey: jest.fn(() => 'cache-key'),
  notificationStorage: { getCachedList: jest.fn(() => []), cacheList: jest.fn() },
}));

import { api } from '@/services/apiClient';
import { ApiError } from '@/types';
import { apiNotificationProvider } from '../services/apiNotificationProvider';

beforeEach(() => jest.clearAllMocks());

test.each([401, 403, 500])('does not hide HTTP %s behind cached notifications', async (status) => {
  const error = new ApiError({ status, message: 'Failure', errorCode: 'failure' });
  (api.get as jest.Mock).mockRejectedValueOnce(error);
  await expect(apiNotificationProvider.list({})).rejects.toBe(error);
});

test('labels a network fallback response as cached', async () => {
  (api.get as jest.Mock).mockRejectedValueOnce(
    new ApiError({ status: 0, message: 'Offline', errorCode: 'network_error' }),
  );
  await expect(apiNotificationProvider.list({})).resolves.toMatchObject({ cached: true });
});
