jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { ApiError } from '@/types';

import { MemoryError, type MemoryProvider } from '../services/memoryProvider';
import { isOfflineError, memoryOutbox, syncMemory } from '../services/memorySync';

const networkError = () => new ApiError({ status: 0, message: 'offline', errorCode: 'network' });

function fakeProvider(overrides: Partial<MemoryProvider> = {}): MemoryProvider {
  return {
    dashboard: jest.fn(),
    latest: jest.fn(),
    history: jest.fn(),
    summary: jest.fn(),
    getMemory: jest.fn(),
    rebuild: jest.fn().mockResolvedValue({ farmId: 'f', created: 0, total: 0, summaries: 0, links: 0 }),
    ...overrides,
  } as MemoryProvider;
}

describe('memorySync', () => {
  beforeEach(() => memoryOutbox.clear());

  it('detects offline errors', () => {
    expect(isOfflineError(networkError())).toBe(true);
    expect(isOfflineError(new MemoryError('network', 'x'))).toBe(true);
    expect(isOfflineError(new MemoryError('unavailable', 'x'))).toBe(false);
    expect(isOfflineError(new Error('other'))).toBe(false);
  });

  it('collapses duplicate rebuilds for the same farm', () => {
    memoryOutbox.enqueue('f1');
    memoryOutbox.enqueue('f1');
    expect(memoryOutbox.count()).toBe(1);
    memoryOutbox.enqueue('f2');
    expect(memoryOutbox.count()).toBe(2);
  });

  it('drains queued rebuilds on reconnect', async () => {
    memoryOutbox.enqueue('f1');
    memoryOutbox.enqueue('f2');
    const provider = fakeProvider();
    const result = await syncMemory(provider);
    expect(result.synced).toBe(2);
    expect(result.remaining).toBe(0);
    expect(provider.rebuild).toHaveBeenCalledTimes(2);
  });

  it('keeps the queue intact while still offline', async () => {
    memoryOutbox.enqueue('f1');
    const provider = fakeProvider({ rebuild: jest.fn().mockRejectedValue(networkError()) });
    const result = await syncMemory(provider);
    expect(result.synced).toBe(0);
    expect(result.remaining).toBe(1);
  });

  it('drops a poison entry on a non-network rejection', async () => {
    memoryOutbox.enqueue('f1');
    const provider = fakeProvider({
      rebuild: jest.fn().mockRejectedValue(new MemoryError('invalid', 'x')),
    });
    const result = await syncMemory(provider);
    expect(result.failed).toBe(1);
    expect(result.remaining).toBe(0);
  });
});
