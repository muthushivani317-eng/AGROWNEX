jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { ApiError } from '@/types';

import { IntelligenceError, type IntelligenceProvider } from '../services/intelligenceProvider';
import {
  intelligenceOutbox,
  isOfflineError,
  syncIntelligence,
} from '../services/intelligenceSync';

const networkError = () => new ApiError({ status: 0, message: 'offline', errorCode: 'network' });

function fakeProvider(overrides: Partial<IntelligenceProvider> = {}): IntelligenceProvider {
  return {
    dashboard: jest.fn(),
    latest: jest.fn(),
    history: jest.fn(),
    getReport: jest.fn(),
    refresh: jest.fn().mockResolvedValue(undefined),
    ...overrides,
  } as IntelligenceProvider;
}

describe('intelligenceSync', () => {
  beforeEach(() => intelligenceOutbox.clear());

  it('detects offline errors', () => {
    expect(isOfflineError(networkError())).toBe(true);
    expect(isOfflineError(new IntelligenceError('network', 'x'))).toBe(true);
    expect(isOfflineError(new IntelligenceError('unavailable', 'x'))).toBe(false);
    expect(isOfflineError(new Error('other'))).toBe(false);
  });

  it('collapses duplicate refreshes for the same farm', () => {
    intelligenceOutbox.enqueue('f1');
    intelligenceOutbox.enqueue('f1');
    expect(intelligenceOutbox.count()).toBe(1);
    intelligenceOutbox.enqueue('f2');
    expect(intelligenceOutbox.count()).toBe(2);
  });

  it('drains queued refreshes on reconnect', async () => {
    intelligenceOutbox.enqueue('f1');
    intelligenceOutbox.enqueue('f2');
    const provider = fakeProvider();
    const result = await syncIntelligence(provider);
    expect(result.synced).toBe(2);
    expect(result.remaining).toBe(0);
    expect(provider.refresh).toHaveBeenCalledTimes(2);
  });

  it('keeps the queue intact while still offline', async () => {
    intelligenceOutbox.enqueue('f1');
    const provider = fakeProvider({ refresh: jest.fn().mockRejectedValue(networkError()) });
    const result = await syncIntelligence(provider);
    expect(result.synced).toBe(0);
    expect(result.remaining).toBe(1);
  });

  it('drops a poison entry on a non-network rejection', async () => {
    intelligenceOutbox.enqueue('f1');
    const provider = fakeProvider({
      refresh: jest.fn().mockRejectedValue(new IntelligenceError('invalid', 'x')),
    });
    const result = await syncIntelligence(provider);
    expect(result.failed).toBe(1);
    expect(result.remaining).toBe(0);
  });
});
