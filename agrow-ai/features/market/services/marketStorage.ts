import { appStorage } from '@/lib/storage';

import { MARKET_FAVOURITES_KEY, MARKET_PRICES_CACHE_KEY } from '../constants';
import type { MarketFavourite, MarketPrice } from '../types';

/**
 * Local market mirror in MMKV (offline cache + local-provider favourites).
 * Prices are cached per filter key so the last-seen list is readable offline.
 */
type PriceCache = Record<string, { items: MarketPrice[]; cachedAt: string }>;

function readPriceCache(): PriceCache {
  return appStorage.getJSON<PriceCache>(MARKET_PRICES_CACHE_KEY) ?? {};
}

function readFavourites(): MarketFavourite[] {
  return appStorage.getJSON<MarketFavourite[]>(MARKET_FAVOURITES_KEY) ?? [];
}

export const marketStorage = {
  cachePrices(filterKey: string, items: MarketPrice[]): void {
    const cache = readPriceCache();
    // An empty response is useful UI state, but not a useful offline fallback.
    // Persisting it would turn a later network/provider failure into a
    // misleading "No prices found" result. Also remove legacy empty entries.
    if (items.length === 0) {
      if (filterKey in cache) {
        delete cache[filterKey];
        appStorage.setJSON(MARKET_PRICES_CACHE_KEY, cache);
      }
      return;
    }
    cache[filterKey] = { items, cachedAt: new Date().toISOString() };
    appStorage.setJSON(MARKET_PRICES_CACHE_KEY, cache);
  },

  getCachedPrices(filterKey: string): MarketPrice[] | null {
    const items = readPriceCache()[filterKey]?.items;
    return items && items.length > 0 ? items : null;
  },

  favourites(): MarketFavourite[] {
    return readFavourites();
  },

  setFavourites(list: MarketFavourite[]): void {
    appStorage.setJSON(MARKET_FAVOURITES_KEY, list);
  },

  addFavourite(fav: MarketFavourite): MarketFavourite[] {
    const list = readFavourites();
    const exists = list.some(
      (f) =>
        f.commodity === fav.commodity &&
        f.market === fav.market &&
        f.district === fav.district,
    );
    const next = exists ? list : [fav, ...list];
    appStorage.setJSON(MARKET_FAVOURITES_KEY, next);
    return next;
  },

  removeFavourite(id: string): MarketFavourite[] {
    const next = readFavourites().filter((f) => f.id !== id);
    appStorage.setJSON(MARKET_FAVOURITES_KEY, next);
    return next;
  },

  clear(): void {
    appStorage.remove(MARKET_PRICES_CACHE_KEY);
    appStorage.remove(MARKET_FAVOURITES_KEY);
  },
};

/** Stable cache key for a set of filters (mirrors the backend cache key). */
export function filterCacheKey(filters: {
  crop?: string | null;
  market?: string | null;
  district?: string | null;
  state?: string | null;
  todayOnly?: boolean;
}): string {
  return [
    filters.crop ?? '',
    filters.market ?? '',
    filters.district ?? '',
    filters.state ?? '',
    filters.todayOnly ? 'today' : 'all',
  ]
    .join('|')
    .toLowerCase();
}
