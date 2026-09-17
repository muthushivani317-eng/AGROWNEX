jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { ApiError } from '@/types';

import { SatelliteError, type SatelliteProvider } from '../services/satelliteProvider';
import { isOfflineError, satelliteOutbox, syncSatellite } from '../services/satelliteSync';

const networkError = () =>
  new ApiError({ status: 0, message: 'offline', errorCode: 'network' });

function fakeProvider(overrides: Partial<SatelliteProvider> = {}): SatelliteProvider {
  return {
    dashboard: jest.fn(),
    history: jest.fn(),
    timeline: jest.fn(),
    alerts: jest.fn(),
    refresh: jest.fn().mockResolvedValue(undefined),
    ...overrides,
  } as unknown as SatelliteProvider;
}

describe('satelliteSync', () => {
  beforeEach(() => satelliteOutbox.clear());

  it('detects connectivity failures', () => {
    expect(isOfflineError(networkError())).toBe(true);
    expect(isOfflineError(new SatelliteError('network', 'x'))).toBe(true);
    expect(isOfflineError(new SatelliteError('provider_error', 'x'))).toBe(false);
    expect(isOfflineError(new Error('other'))).toBe(false);
  });

  it('collapses duplicate refresh requests for the same farm', () => {
    satelliteOutbox.enqueue('farm-1');
    satelliteOutbox.enqueue('farm-1');
    satelliteOutbox.enqueue('farm-2');
    expect(satelliteOutbox.count()).toBe(2);
  });

  it('drains queued refreshes on reconnect', async () => {
    satelliteOutbox.enqueue('farm-1');
    satelliteOutbox.enqueue('farm-2');
    const provider = fakeProvider();
    const result = await syncSatellite(provider);
    expect(result.synced).toBe(2);
    expect(result.remaining).toBe(0);
    expect(provider.refresh).toHaveBeenCalledWith('farm-1', true);
    expect(provider.refresh).toHaveBeenCalledWith('farm-2', true);
  });

  it('keeps the queue intact while still offline', async () => {
    satelliteOutbox.enqueue('farm-1');
    const provider = fakeProvider({
      refresh: jest.fn().mockRejectedValue(networkError()),
    });
    const result = await syncSatellite(provider);
    expect(result.synced).toBe(0);
    expect(result.remaining).toBe(1);
  });

  it('drops a poison entry on a non-network rejection', async () => {
    satelliteOutbox.enqueue('farm-1');
    const provider = fakeProvider({
      refresh: jest.fn().mockRejectedValue(new SatelliteError('provider_error', 'x')),
    });
    const result = await syncSatellite(provider);
    expect(result.failed).toBe(1);
    expect(result.remaining).toBe(0);
  });

  it('removes and clears outbox entries', () => {
    satelliteOutbox.enqueue('farm-1');
    const [entry] = satelliteOutbox.all();
    satelliteOutbox.remove(entry.entryId);
    expect(satelliteOutbox.count()).toBe(0);
    satelliteOutbox.enqueue('farm-3');
    satelliteOutbox.clear();
    expect(satelliteOutbox.count()).toBe(0);
  });
});
