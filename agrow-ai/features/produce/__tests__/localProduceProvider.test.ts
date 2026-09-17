jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import dayjs from 'dayjs';

import { localProduceProvider } from '../services/localProduceProvider';
import { ProduceError } from '../services/produceProvider';
import { produceStorage } from '../services/produceStorage';
import type { ProduceInput } from '../types';
import { useAuthStore } from '@/features/auth/store/authStore';

function signInAs(id: string) {
  useAuthStore.setState({ user: { id } as never, status: 'authenticated' });
}

function input(overrides: Partial<ProduceInput> = {}): ProduceInput {
  return {
    farmId: 'farm-1',
    cropName: 'Paddy',
    quantity: 20,
    unit: 'quintal',
    expectedHarvestDate: dayjs().add(10, 'day').format('YYYY-MM-DD'),
    ...overrides,
  };
}

describe('localProduceProvider', () => {
  beforeEach(() => { signInAs('farmer-a'); produceStorage.clear(); });

  it('does not expose farmer A offline listings after logout and farmer B login', async () => {
    await localProduceProvider.create(input({ cropName: 'Farmer A paddy' }));
    expect((await localProduceProvider.list({})).total).toBe(1);
    useAuthStore.setState({ user: null, status: 'unauthenticated' });
    expect((await localProduceProvider.list({})).total).toBe(0);
    signInAs('farmer-b');
    produceStorage.clear();
    expect((await localProduceProvider.list({})).total).toBe(0);
  });

  it('creates an offer, acknowledges it (mock) and records status history', async () => {
    const offer = await localProduceProvider.create(input());
    expect(offer.cropName).toBe('Paddy');
    expect(offer.status).toBe('submitted');
    expect(offer.procurementChannel).toBe('mock');
    expect(offer.procurementReference).toMatch(/^MOCK-/);
    expect(offer.statusHistory).toHaveLength(1);
    // No verified price offline → snapshot stays null (never fabricated).
    expect(offer.currentMarketPriceSnapshot).toBeNull();
    expect(offer.insight?.estimatedMarketValue).toBeNull();
  });

  it('does not acknowledge a draft offer', async () => {
    const offer = await localProduceProvider.create(input({ status: 'draft' }));
    expect(offer.procurementReference).toBeNull();
    expect(offer.status).toBe('draft');
  });

  it('lists and filters offers by crop', async () => {
    await localProduceProvider.create(input({ cropName: 'Paddy' }));
    await localProduceProvider.create(input({ cropName: 'Maize' }));
    const all = await localProduceProvider.list({});
    expect(all.total).toBe(2);
    const paddy = await localProduceProvider.list({ crop: 'paddy' });
    expect(paddy.total).toBe(1);
    expect(paddy.items[0].cropName).toBe('Paddy');
  });

  it('recomputes the harvest window on read', async () => {
    const offer = await localProduceProvider.create(
      input({ expectedHarvestDate: dayjs().add(3, 'day').format('YYYY-MM-DD') }),
    );
    const fetched = await localProduceProvider.get(offer.id);
    expect(fetched.insight?.harvestWindow).toBe('this_week');
  });

  it('lists upcoming (future, submitted/planned) soonest first', async () => {
    await localProduceProvider.create(
      input({ cropName: 'Later', expectedHarvestDate: dayjs().add(20, 'day').format('YYYY-MM-DD') }),
    );
    await localProduceProvider.create(
      input({ cropName: 'Soon', expectedHarvestDate: dayjs().add(2, 'day').format('YYYY-MM-DD') }),
    );
    const upcoming = await localProduceProvider.upcoming();
    expect(upcoming.items.map((o) => o.cropName)).toEqual(['Soon', 'Later']);
  });

  it('moves concluded offers into history', async () => {
    const offer = await localProduceProvider.create(input({ cropName: 'Done' }));
    await localProduceProvider.update(offer.id, {
      ...input({ cropName: 'Done' }),
      status: 'harvested',
    });
    const history = await localProduceProvider.history();
    expect(history.items.map((o) => o.cropName)).toContain('Done');
    const all = await localProduceProvider.upcoming();
    expect(all.items.map((o) => o.cropName)).not.toContain('Done');
  });

  it('records status history on a status change', async () => {
    const offer = await localProduceProvider.create(input());
    const updated = await localProduceProvider.update(offer.id, {
      ...input(),
      status: 'withdrawn',
    });
    expect(updated.statusHistory.map((h) => h.newStatus)).toEqual([
      'submitted',
      'withdrawn',
    ]);
  });

  it('adds an image and updates the count/thumbnail', async () => {
    const offer = await localProduceProvider.create(input());
    const withImage = await localProduceProvider.addImage(offer.id, {
      imageUrl: 'https://cdn/r2/a.jpg',
    });
    expect(withImage.imageCount).toBe(1);
    expect(withImage.thumbnailUrl).toBe('https://cdn/r2/a.jpg');
  });

  it('soft-deletes an offer', async () => {
    const offer = await localProduceProvider.create(input());
    await localProduceProvider.remove(offer.id);
    await expect(localProduceProvider.get(offer.id)).rejects.toBeInstanceOf(ProduceError);
  });

  it('throws for an unknown offer', async () => {
    await expect(localProduceProvider.get('nope')).rejects.toBeInstanceOf(ProduceError);
  });
});
