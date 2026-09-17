jest.mock('@/services/apiClient', () => ({ api: { get: jest.fn() } }));
import { api } from '@/services/apiClient';
import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { fallbackHarvestReadiness } from '../harvestReadiness';
import { getCurrentReadiness } from '../services/harvestReadinessApi';

const cacheKey = 'agrowai.harvest-readiness.f1.c1';
beforeEach(() => {
  jest.clearAllMocks();
  appStorage.setJSON(cacheKey, { ...fallbackHarvestReadiness(), id: 'old', farmId: 'f1', cropCycleId: 'c1' });
});
afterEach(() => appStorage.remove(cacheKey));
test('an authoritative empty response clears obsolete cached assessment', async () => {
  (api.get as jest.Mock).mockResolvedValueOnce(null);
  await getCurrentReadiness('f1', 'c1');
  expect(appStorage.getJSON(cacheKey)).toBeNull();
  const error = new ApiError({ status: 0, errorCode: 'network_error', message: 'Offline' });
  (api.get as jest.Mock).mockRejectedValueOnce(error);
  await expect(getCurrentReadiness('f1', 'c1')).rejects.toBe(error);
});
test('network fallback is explicitly marked cached', async () => {
  (api.get as jest.Mock).mockRejectedValueOnce(new ApiError({ status: 0, errorCode: 'network_error', message: 'Offline' }));
  await expect(getCurrentReadiness('f1', 'c1')).resolves.toMatchObject({ id: 'old', cached: true });
});
test.each([401, 403, 500])('does not hide failure %s with cached evidence', async status => {
  const error = new ApiError({ status, errorCode: 'failure', message: 'Failure' });
  (api.get as jest.Mock).mockRejectedValueOnce(error);
  await expect(getCurrentReadiness('f1', 'c1')).rejects.toBe(error);
});
