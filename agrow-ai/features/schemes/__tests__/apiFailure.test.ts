jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn() } }));
jest.mock('../services/schemeStorage', () => ({
  queryCacheKey: () => 'query', listCacheKey: () => 'list',
  schemeStorage: { getCachedList: jest.fn(() => []), cacheList: jest.fn() },
}));
import { api } from '@/services/apiClient';
import { ApiError } from '@/types';
import { apiSchemeProvider } from '../services/apiSchemeProvider';

beforeEach(() => jest.clearAllMocks());
const reads = [() => apiSchemeProvider.list({}), () => apiSchemeProvider.eligible({}), () => apiSchemeProvider.recommended({})];
test.each([401, 403, 500])('does not mask HTTP %s with cached schemes', async status => {
  for (const read of reads) {
    const error = new ApiError({ status, message: 'Failure', errorCode: 'failure' });
    (api.get as jest.Mock).mockRejectedValueOnce(error);
    await expect(read()).rejects.toBe(error);
  }
});
test('labels all network fallback responses as cached', async () => {
  for (const read of reads) {
    (api.get as jest.Mock).mockRejectedValueOnce(new ApiError({ status: 0, message: 'Offline', errorCode: 'network_error' }));
    await expect(read()).resolves.toMatchObject({ cached: true });
  }
});
