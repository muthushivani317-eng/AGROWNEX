import {
  apiToFavourite,
  apiToHistory,
  apiToPage,
  apiToPrice,
  apiToSearchResult,
} from '../services/marketMapper';
import type {
  ApiMarketFavourite,
  ApiMarketHistory,
  ApiMarketPrice,
  ApiMarketPricePage,
} from '../types';

const apiPrice: ApiMarketPrice = {
  id: 'p1',
  commodity: 'Paddy',
  variety: 'Common',
  category: 'cereal',
  market: 'Thanjavur',
  district: 'Thanjavur',
  state: 'Tamil Nadu',
  minimum_price: 1980,
  maximum_price: 2120,
  modal_price: 2050,
  unit: 'quintal',
  price_date: '2026-07-11',
  source: 'agmarknet',
  verified: true,
  is_stale: false,
  age_days: 0,
  updated_at: '2026-07-11T06:00:00Z',
};

describe('apiToPrice', () => {
  it('maps snake_case to camelCase', () => {
    const price = apiToPrice(apiPrice);
    expect(price.minimumPrice).toBe(1980);
    expect(price.maximumPrice).toBe(2120);
    expect(price.modalPrice).toBe(2050);
    expect(price.priceDate).toBe('2026-07-11');
    expect(price.verified).toBe(true);
    expect(price.isStale).toBe(false);
    expect(price.ageDays).toBe(0);
    expect(price.category).toBe('cereal');
  });
});

describe('apiToPage', () => {
  it('maps a paginated envelope', () => {
    const dto: ApiMarketPricePage = {
      items: [apiPrice],
      page: 1,
      page_size: 20,
      total: 1,
      total_pages: 1,
    };
    const page = apiToPage(dto);
    expect(page.pageSize).toBe(20);
    expect(page.totalPages).toBe(1);
    expect(page.items[0].commodity).toBe('Paddy');
  });
});

describe('apiToHistory', () => {
  it('maps history points', () => {
    const dto: ApiMarketHistory = {
      commodity: 'Paddy',
      variety: 'Common',
      market: 'Thanjavur',
      district: 'Thanjavur',
      state: 'Tamil Nadu',
      unit: 'quintal',
      points: [
        {
          recorded_date: '2026-07-10',
          minimum_price: 1900,
          maximum_price: 2100,
          modal_price: 2000,
          unit: 'quintal',
        },
      ],
    };
    const history = apiToHistory(dto);
    expect(history.points).toHaveLength(1);
    expect(history.points[0].recordedDate).toBe('2026-07-10');
    expect(history.points[0].modalPrice).toBe(2000);
  });
});

describe('apiToFavourite', () => {
  it('maps a favourite with a latest price', () => {
    const dto: ApiMarketFavourite = {
      id: 'f1',
      commodity: 'Paddy',
      market: 'Thanjavur',
      district: 'Thanjavur',
      state: 'Tamil Nadu',
      created_at: '2026-07-11T00:00:00Z',
      latest: apiPrice,
    };
    const favourite = apiToFavourite(dto);
    expect(favourite.market).toBe('Thanjavur');
    expect(favourite.latest?.modalPrice).toBe(2050);
  });

  it('maps a favourite without a latest price', () => {
    const dto: ApiMarketFavourite = {
      id: 'f2',
      commodity: 'Onion',
      market: 'Madurai',
      district: 'Madurai',
      state: 'Tamil Nadu',
      created_at: '2026-07-11T00:00:00Z',
      latest: null,
    };
    expect(apiToFavourite(dto).latest).toBeNull();
  });
});

describe('apiToSearchResult', () => {
  it('maps a search suggestion', () => {
    const result = apiToSearchResult({
      type: 'market',
      value: 'Thanjavur',
      label: 'Thanjavur',
    });
    expect(result.type).toBe('market');
    expect(result.value).toBe('Thanjavur');
  });
});
