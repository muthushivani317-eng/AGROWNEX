jest.mock('@/utils/id', () => {
  let id = 0;
  return { uuid: () => `isolated-${++id}` };
});

import { useAuthStore } from '@/features/auth/store/authStore';

import { localProduceProvider } from '../services/localProduceProvider';
import type { ProduceProvider } from '../services/produceProvider';
import { produceStorage } from '../services/produceStorage';
import { produceOutbox, syncProduce } from '../services/produceSync';
import type { ProduceInput } from '../types';

const listing: ProduceInput = {
  farmId: 'farm-a',
  cropName: 'Paddy',
  availabilityType: 'available_now',
  category: 'grains',
  productName: 'Paddy',
  quantity: 10,
  availableQuantity: 10,
  unit: 'kg',
  expectedHarvestDate: null,
};

function signInAs(id: string): void {
  useAuthStore.setState({ user: { id } as never, status: 'authenticated' });
}

function logout(): void {
  useAuthStore.setState({ user: null, status: 'unauthenticated' });
}

describe('produce offline account isolation', () => {
  beforeEach(() => {
    signInAs('farmer-a');
    produceStorage.clear();
    produceOutbox.clear();
    signInAs('farmer-b');
    produceStorage.clear();
    produceOutbox.clear();
    signInAs('farmer-a');
  });

  it('prevents Farmer B from reading Farmer A cached listings after logout and account switch', async () => {
    await localProduceProvider.create(listing);
    expect((await localProduceProvider.list({})).total).toBe(1);

    logout();
    expect((await localProduceProvider.list({})).items).toEqual([]);
    signInAs('farmer-b');
    expect((await localProduceProvider.list({})).items).toEqual([]);
  });

  it('prevents Farmer B from reading or replaying Farmer A outbox after logout and account switch', async () => {
    produceOutbox.enqueue({ op: 'create', offerId: 'farmer-a-offer', input: listing });
    expect(produceOutbox.count()).toBe(1);

    logout();
    expect(produceOutbox.all()).toEqual([]);
    signInAs('farmer-b');
    expect(produceOutbox.all()).toEqual([]);

    const create = jest.fn();
    const provider = { create } as unknown as ProduceProvider;
    const result = await syncProduce(provider);
    expect(create).not.toHaveBeenCalled();
    expect(result).toEqual({ synced: 0, failed: 0, remaining: 0 });
  });
});
