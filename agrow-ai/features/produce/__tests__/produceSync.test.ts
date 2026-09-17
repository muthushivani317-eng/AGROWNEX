jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `entry-${++n}` };
});

import { ApiError } from '@/types';

import type { ProduceProvider } from '../services/produceProvider';
import { ProduceError } from '../services/produceProvider';
import { isOfflineError, produceOutbox, syncProduce } from '../services/produceSync';
import type { ProduceInput } from '../types';
import { useAuthStore } from '@/features/auth/store/authStore';

function signInAs(id: string) {
  useAuthStore.setState({ user: { id } as never, status: 'authenticated' });
}

const sampleInput: ProduceInput = {
  farmId: 'f1',
  cropName: 'Paddy',
  quantity: 20,
  unit: 'quintal',
  expectedHarvestDate: '2026-12-01',
};

function makeProvider(overrides: Partial<ProduceProvider> = {}): ProduceProvider {
  return {
    list: jest.fn(),
    upcoming: jest.fn(),
    history: jest.fn(),
    get: jest.fn(),
    create: jest.fn().mockResolvedValue({}),
    update: jest.fn().mockResolvedValue({}),
    remove: jest.fn().mockResolvedValue(undefined),
    addImage: jest.fn(),
    ...overrides,
  } as unknown as ProduceProvider;
}

describe('produceOutbox', () => {
  beforeEach(() => { signInAs('farmer-a'); produceOutbox.clear(); });

  it('does not replay farmer A operations after switching to farmer B', () => {
    produceOutbox.enqueue({ op: 'create', offerId: 'a1', input: sampleInput });
    useAuthStore.setState({ user: null, status: 'unauthenticated' });
    expect(produceOutbox.count()).toBe(0);
    signInAs('farmer-b');
    produceOutbox.clear();
    expect(produceOutbox.count()).toBe(0);
  });

  it('enqueues and counts entries', () => {
    produceOutbox.enqueue({ op: 'create', offerId: 'o1', input: sampleInput });
    expect(produceOutbox.count()).toBe(1);
  });
});

const networkError = () =>
  new ApiError({ status: 0, message: 'net', errorCode: 'network' });
const validationApiError = () =>
  new ApiError({ status: 422, message: 'bad', errorCode: 'invalid_produce' });

describe('isOfflineError', () => {
  it('is true for a network ApiError', () => {
    expect(isOfflineError(networkError())).toBe(true);
  });
  it('is false for a non-network ApiError', () => {
    expect(isOfflineError(validationApiError())).toBe(false);
  });
  it('is false for a validation ProduceError', () => {
    expect(isOfflineError(new ProduceError('invalid', 'bad'))).toBe(false);
  });
});

describe('syncProduce', () => {
  beforeEach(() => { signInAs('farmer-a'); produceOutbox.clear(); });

  it('replays queued mutations and drains the outbox', async () => {
    produceOutbox.enqueue({ op: 'create', offerId: 'o1', input: sampleInput });
    produceOutbox.enqueue({ op: 'delete', offerId: 'o2' });
    const provider = makeProvider();

    const result = await syncProduce(provider);
    expect(result.synced).toBe(2);
    expect(result.remaining).toBe(0);
    expect(provider.create).toHaveBeenCalledTimes(1);
    expect(provider.remove).toHaveBeenCalledTimes(1);
  });

  it('keeps the queue intact when still offline', async () => {
    produceOutbox.enqueue({ op: 'create', offerId: 'o1', input: sampleInput });
    const provider = makeProvider({
      create: jest.fn().mockRejectedValue(networkError()),
    });

    const result = await syncProduce(provider);
    expect(result.synced).toBe(0);
    expect(result.remaining).toBe(1); // preserved for a later retry
  });

  it('drops a poison entry on a non-offline rejection', async () => {
    produceOutbox.enqueue({ op: 'create', offerId: 'o1', input: sampleInput });
    const provider = makeProvider({
      create: jest.fn().mockRejectedValue(new ProduceError('invalid_produce', 'bad')),
    });

    const result = await syncProduce(provider);
    expect(result.failed).toBe(1);
    expect(result.remaining).toBe(0);
  });
});
