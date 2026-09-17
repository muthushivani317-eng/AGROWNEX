jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { ApiError } from '@/types';

import { SoilError, type SoilProvider } from '../services/soilProvider';
import { isOfflineError, soilOutbox, syncSoil } from '../services/soilSync';
import type { SoilReportInput } from '../types';

const networkError = () =>
  new ApiError({ status: 0, message: 'offline', errorCode: 'network' });

const input: SoilReportInput = {
  farmId: 'f1',
  source: 'self',
  values: { ph: 6.5 },
};

function fakeProvider(overrides: Partial<SoilProvider> = {}): SoilProvider {
  return {
    dashboard: jest.fn(),
    latest: jest.fn(),
    history: jest.fn(),
    recommendations: jest.fn(),
    submitReport: jest.fn().mockResolvedValue(undefined),
    ...overrides,
  } as SoilProvider;
}

describe('soilSync', () => {
  beforeEach(() => soilOutbox.clear());

  it('detects offline errors', () => {
    expect(isOfflineError(networkError())).toBe(true);
    expect(isOfflineError(new SoilError('network', 'x'))).toBe(true);
    expect(isOfflineError(new SoilError('soil_data_unavailable', 'x'))).toBe(false);
    expect(isOfflineError(new Error('other'))).toBe(false);
  });

  it('drains queued soil reports on reconnect', async () => {
    soilOutbox.enqueue(input);
    soilOutbox.enqueue({ ...input, values: { nitrogen: 300 } });
    expect(soilOutbox.count()).toBe(2);

    const provider = fakeProvider();
    const result = await syncSoil(provider);
    expect(result.synced).toBe(2);
    expect(result.remaining).toBe(0);
    expect(provider.submitReport).toHaveBeenCalledTimes(2);
  });

  it('keeps the queue intact while still offline', async () => {
    soilOutbox.enqueue(input);
    const provider = fakeProvider({
      submitReport: jest.fn().mockRejectedValue(networkError()),
    });
    const result = await syncSoil(provider);
    expect(result.synced).toBe(0);
    expect(result.remaining).toBe(1);
  });

  it('drops a poison entry on a non-network rejection', async () => {
    soilOutbox.enqueue(input);
    const provider = fakeProvider({
      submitReport: jest.fn().mockRejectedValue(new SoilError('invalid', 'x')),
    });
    const result = await syncSoil(provider);
    expect(result.failed).toBe(1);
    expect(result.remaining).toBe(0);
  });
});
