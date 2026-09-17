jest.mock('@/services/apiClient', () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

import { api } from '@/services/apiClient';
import { ApiError } from '@/types';

import { apiMarketProvider } from '../services/apiMarketProvider';
import { MarketError } from '../services/marketProvider';
import { filterCacheKey, marketStorage } from '../services/marketStorage';
import type { ApiMarketPricePage, MarketPrice } from '../types';

const filters = { crop: 'Paddy', page: 1, pageSize: 20 };

const cachedPrice: MarketPrice = {
  id: 'cached-1',
  commodity: 'Paddy',
  variety: 'Common',
  category: 'cereal',
  market: 'Thanjavur',
  district: 'Thanjavur',
  state: 'Tamil Nadu',
  minimumPrice: 1980,
  maximumPrice: 2120,
  modalPrice: 2050,
  unit: 'quintal',
  priceDate: '2026-08-26',
  source: 'agmarknet',
  verified: true,
  isStale: false,
  ageDays: 0,
  updatedAt: '2026-08-26T06:00:00Z',
};

const emptyPage: ApiMarketPricePage = {
  items: [],
  page: 1,
  page_size: 20,
  total: 0,
  total_pages: 0,
};

describe('apiMarketProvider prices', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    marketStorage.clear();
  });

  it('keeps a genuine successful empty response distinct from provider failure', async () => {
    (api.get as jest.Mock).mockResolvedValueOnce(emptyPage);

    await expect(apiMarketProvider.prices(filters)).resolves.toMatchObject({
      items: [],
      total: 0,
    });
    expect(marketStorage.getCachedPrices(filterCacheKey(filters))).toBeNull();
  });

  it('does not let a previously cached empty result mask a later error', async () => {
    marketStorage.cachePrices(filterCacheKey(filters), []);
    (api.get as jest.Mock).mockRejectedValueOnce(
      new ApiError({
        status: 0,
        message: 'Network Error',
        errorCode: 'network_error',
      }),
    );

    await expect(apiMarketProvider.prices(filters)).rejects.toMatchObject({
      errorCode: 'network_error',
    });
  });

  it('surfaces structured market unavailability even when a non-empty cache exists', async () => {
    marketStorage.cachePrices(filterCacheKey(filters), [cachedPrice]);
    (api.get as jest.Mock).mockRejectedValueOnce(
      new ApiError({
        status: 503,
        message: 'Market data unavailable',
        errorCode: 'market_data_unavailable',
      }),
    );

    await expect(apiMarketProvider.prices(filters)).rejects.toEqual(
      expect.objectContaining<Partial<MarketError>>({
        name: 'MarketError',
        code: 'market_data_unavailable',
        message: 'market.providerUnavailable',
      }),
    );
  });

  it('does not misclassify an unrelated 503 as market provider unavailability', async () => {
    const maintenanceError = new ApiError({
      status: 503,
      message: 'Service maintenance',
      errorCode: 'service_maintenance',
    });
    (api.get as jest.Mock).mockRejectedValueOnce(maintenanceError);

    await expect(apiMarketProvider.prices(filters)).rejects.toBe(
      maintenanceError,
    );
  });

  it('continues to serve a non-empty verified cache during a network outage', async () => {
    marketStorage.cachePrices(filterCacheKey(filters), [cachedPrice]);
    (api.get as jest.Mock).mockRejectedValueOnce(
      new ApiError({
        status: 0,
        message: 'Network Error',
        errorCode: 'network_error',
      }),
    );

    await expect(apiMarketProvider.prices(filters)).resolves.toMatchObject({
      items: [cachedPrice],
      fromCache: true,
      total: 1,
    });
  });
});
