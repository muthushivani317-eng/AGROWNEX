jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { localMarketProvider } from '../services/localMarketProvider';
import { MarketError } from '../services/marketProvider';
import { marketStorage } from '../services/marketStorage';

describe('localMarketProvider', () => {
  beforeEach(() => marketStorage.clear());

  it('returns deterministic sample prices', async () => {
    const page = await localMarketProvider.prices({});
    expect(page.total).toBeGreaterThan(0);
    expect(page.items[0].verified).toBe(true);
    expect(page.items[0].modalPrice).toBeGreaterThan(0);
  });

  it('filters by crop', async () => {
    const page = await localMarketProvider.prices({ crop: 'paddy' });
    expect(page.items.every((p) => p.commodity === 'Paddy')).toBe(true);
  });

  it('filters by district', async () => {
    const page = await localMarketProvider.prices({ district: 'salem' });
    expect(page.items.length).toBeGreaterThan(0);
    expect(page.items.every((p) => p.district === 'Salem')).toBe(true);
  });

  it('paginates', async () => {
    const page1 = await localMarketProvider.prices({ page: 1, pageSize: 3 });
    expect(page1.items).toHaveLength(3);
    const page2 = await localMarketProvider.prices({ page: 2, pageSize: 3 });
    expect(page2.items.length).toBeGreaterThan(0);
    expect(page1.items[0].id).not.toBe(page2.items[0].id);
  });

  it('returns search facets across crops, markets and districts', async () => {
    const results = await localMarketProvider.search('tha');
    const types = new Set(results.map((r) => r.type));
    expect(types.has('market') || types.has('district')).toBe(true);
    const crops = await localMarketProvider.search('paddy');
    expect(crops.some((r) => r.type === 'crop' && r.value === 'Paddy')).toBe(true);
  });

  it('builds a history series', async () => {
    const history = await localMarketProvider.history('Paddy', 'Thanjavur');
    expect(history.points.length).toBeGreaterThan(1);
    expect(history.market).toBe('Thanjavur');
  });

  it('adds, lists and prevents duplicate favourites', async () => {
    const fav = await localMarketProvider.addFavourite({
      commodity: 'Paddy',
      market: 'Thanjavur',
      district: 'Thanjavur',
      state: 'Tamil Nadu',
    });
    expect(fav.latest).not.toBeNull();
    expect(await localMarketProvider.favourites()).toHaveLength(1);

    await expect(
      localMarketProvider.addFavourite({
        commodity: 'Paddy',
        market: 'Thanjavur',
        district: 'Thanjavur',
        state: 'Tamil Nadu',
      }),
    ).rejects.toBeInstanceOf(MarketError);
  });

  it('removes a favourite', async () => {
    const fav = await localMarketProvider.addFavourite({
      commodity: 'Onion',
      market: 'Madurai',
      district: 'Madurai',
      state: 'Tamil Nadu',
    });
    await localMarketProvider.removeFavourite(fav.id);
    expect(await localMarketProvider.favourites()).toHaveLength(0);
  });
});
