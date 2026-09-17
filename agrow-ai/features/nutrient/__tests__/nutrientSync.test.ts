jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { ApiError } from '@/types';

import { NutrientError, type NutrientProvider } from '../services/nutrientProvider';
import { isOfflineError, nutrientOutbox, syncNutrient } from '../services/nutrientSync';
import type { AnalyzeInput } from '../types';

const networkError = () =>
  new ApiError({ status: 0, message: 'offline', errorCode: 'network' });

const input: AnalyzeInput = {
  imageBase64: 'x',
  mimeType: 'image/jpeg',
  imageUri: 'file://leaf.jpg',
  language: 'en',
  captureMethod: 'camera',
  farmId: 'farm-1',
};

function fakeProvider(overrides: Partial<NutrientProvider> = {}): NutrientProvider {
  return {
    analyze: jest.fn().mockResolvedValue(undefined),
    history: jest.fn(),
    latest: jest.fn(),
    recommendations: jest.fn(),
    getReport: jest.fn(),
    ...overrides,
  } as unknown as NutrientProvider;
}

describe('nutrientSync', () => {
  beforeEach(() => nutrientOutbox.clear());

  it('detects connectivity failures', () => {
    expect(isOfflineError(networkError())).toBe(true);
    expect(isOfflineError(new NutrientError('network', 'x'))).toBe(true);
    expect(isOfflineError(new NutrientError('not_found', 'x'))).toBe(false);
    expect(isOfflineError(new Error('other'))).toBe(false);
  });

  it('drains queued analyses on reconnect', async () => {
    nutrientOutbox.enqueue(input);
    nutrientOutbox.enqueue({ ...input, farmId: 'farm-2' });
    expect(nutrientOutbox.count()).toBe(2);

    const provider = fakeProvider();
    const result = await syncNutrient(provider);
    expect(result.synced).toBe(2);
    expect(result.remaining).toBe(0);
    expect(provider.analyze).toHaveBeenCalledTimes(2);
  });

  it('keeps the queue intact while still offline', async () => {
    nutrientOutbox.enqueue(input);
    const provider = fakeProvider({
      analyze: jest.fn().mockRejectedValue(networkError()),
    });
    const result = await syncNutrient(provider);
    expect(result.synced).toBe(0);
    expect(result.remaining).toBe(1);
  });

  it('drops a poison entry on a non-network rejection', async () => {
    nutrientOutbox.enqueue(input);
    const provider = fakeProvider({
      analyze: jest.fn().mockRejectedValue(new NutrientError('bad', 'x')),
    });
    const result = await syncNutrient(provider);
    expect(result.failed).toBe(1);
    expect(result.remaining).toBe(0);
  });

  it('removes and clears outbox entries', () => {
    nutrientOutbox.enqueue(input);
    const [entry] = nutrientOutbox.all();
    nutrientOutbox.remove(entry.entryId);
    expect(nutrientOutbox.count()).toBe(0);
    nutrientOutbox.enqueue(input);
    nutrientOutbox.clear();
    expect(nutrientOutbox.count()).toBe(0);
  });
});
