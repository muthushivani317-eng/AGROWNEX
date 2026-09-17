import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError } from '@/types';

import { DEFAULT_PAGE_SIZE, HISTORY_DAYS } from '../constants';
import type {
  AddFavouriteInput,
  ApiMarketFavourite,
  ApiMarketHistory,
  ApiMarketPricePage,
  ApiMarketSearchResult,
  MarketFavourite,
  MarketFilters,
  MarketHistory,
  MarketPricePage,
  MarketSearchResult,
} from '../types';
import {
  apiToFavourite,
  apiToHistory,
  apiToPage,
  apiToSearchResult,
} from './marketMapper';
import { filterCacheKey, marketStorage } from './marketStorage';
import { MarketError, type MarketProvider } from './marketProvider';

/**
 * Backend market provider (docs/API_CONTRACT.md → MARKET). Every successful
 * price fetch is mirrored to MMKV so the last-seen list stays readable offline;
 * on a network failure the cached list is served instead of erroring.
 */
export const apiMarketProvider: MarketProvider = {
  async prices(filters: MarketFilters): Promise<MarketPricePage> {
    const url = filters.todayOnly ? endpoints.market.today : endpoints.market.root;
    const params = {
      crop: filters.crop ?? undefined,
      market: filters.market ?? undefined,
      district: filters.district ?? undefined,
      state: filters.state ?? undefined,
      page: filters.page ?? 1,
      page_size: filters.pageSize ?? DEFAULT_PAGE_SIZE,
    };
    const key = filterCacheKey(filters);
    try {
      const dto = await api.get<ApiMarketPricePage>(url, { params });
      const page = apiToPage(dto);
      if ((page.page ?? 1) === 1) marketStorage.cachePrices(key, page.items);
      return page;
    } catch (err) {
      // A provider outage is not an empty search result. Never hide the
      // backend's actionable 503 behind cached data (especially legacy empty
      // cache entries); let the screen render its unavailable + Retry state.
      if (
        err instanceof ApiError &&
        err.errorCode === 'market_data_unavailable'
      ) {
        throw new MarketError(
          'market_data_unavailable',
          'market.providerUnavailable',
        );
      }
      // Offline / server error → fall back to the last cached list for this filter.
      const cached = marketStorage.getCachedPrices(key);
      if (cached && cached.length > 0 && err instanceof ApiError) {
        return {
          fromCache: true,
          items: cached,
          page: 1,
          pageSize: cached.length,
          total: cached.length,
          totalPages: 1,
        };
      }
      throw err;
    }
  },

  async history(
    crop: string,
    market: string,
    district?: string | null,
  ): Promise<MarketHistory> {
    const dto = await api.get<ApiMarketHistory>(endpoints.market.history, {
      params: { crop, market, district: district ?? undefined, days: HISTORY_DAYS },
    });
    return apiToHistory(dto);
  },

  async search(term: string): Promise<MarketSearchResult[]> {
    const dto = await api.get<ApiMarketSearchResult[]>(endpoints.market.search, {
      params: { q: term },
    });
    return dto.map(apiToSearchResult);
  },

  async favourites(): Promise<MarketFavourite[]> {
    const dto = await api.get<ApiMarketFavourite[]>(endpoints.market.favourites);
    const favourites = dto.map(apiToFavourite);
    marketStorage.setFavourites(favourites);
    return favourites;
  },

  async addFavourite(input: AddFavouriteInput): Promise<MarketFavourite> {
    const dto = await api.post<ApiMarketFavourite>(endpoints.market.favourites, {
      commodity: input.commodity,
      market: input.market,
      district: input.district,
      state: input.state,
    });
    const favourite = apiToFavourite(dto);
    marketStorage.addFavourite(favourite);
    return favourite;
  },

  async removeFavourite(id: string): Promise<void> {
    await api.delete<null>(endpoints.market.favourite(id));
    marketStorage.removeFavourite(id);
  },
};
