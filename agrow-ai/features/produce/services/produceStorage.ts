import { appStorage } from '@/lib/storage';

import { PRODUCE_CACHE_KEY, PRODUCE_LOCAL_KEY } from '../constants';
import type { ProduceListParams, ProduceOffer, ProduceOfferDetail } from '../types';
import { currentProduceUserId, discardUnscopedProduceData, produceScopedKey } from './produceUserScope';

/**
 * Local produce store in MMKV:
 *  - an offline **cache** of the last-seen API lists (keyed by view/filter) so
 *    offers stay readable offline, and
 *  - the **local-provider** offers (full detail records) that back the app when
 *    no verified backend is configured / in dev.
 */
type ListCache = Record<string, { items: ProduceOffer[]; cachedAt: string }>;

function readCache(userId: string): ListCache {
  discardUnscopedProduceData(PRODUCE_CACHE_KEY, PRODUCE_LOCAL_KEY);
  return appStorage.getJSON<ListCache>(produceScopedKey(PRODUCE_CACHE_KEY, userId)) ?? {};
}

function readLocal(userId: string): Record<string, ProduceOfferDetail> {
  discardUnscopedProduceData(PRODUCE_CACHE_KEY, PRODUCE_LOCAL_KEY);
  return appStorage.getJSON<Record<string, ProduceOfferDetail>>(produceScopedKey(PRODUCE_LOCAL_KEY, userId)) ?? {};
}

export const produceStorage = {
  // --- Offline cache (API provider) ---
  cacheList(key: string, items: ProduceOffer[]): void {
    const userId = currentProduceUserId();
    if (!userId) return;
    const cache = readCache(userId);
    cache[key] = { items, cachedAt: new Date().toISOString() };
    appStorage.setJSON(produceScopedKey(PRODUCE_CACHE_KEY, userId), cache);
  },

  getCachedList(key: string): ProduceOffer[] | null {
    const userId = currentProduceUserId();
    return userId ? readCache(userId)[key]?.items ?? null : null;
  },

  // --- Local provider store ---
  localOffers(): ProduceOfferDetail[] {
    const userId = currentProduceUserId();
    if (!userId) return [];
    return Object.values(readLocal(userId)).sort((a, b) =>
      b.createdAt.localeCompare(a.createdAt),
    );
  },

  getLocal(id: string): ProduceOfferDetail | null {
    const userId = currentProduceUserId();
    return userId ? readLocal(userId)[id] ?? null : null;
  },

  upsertLocal(offer: ProduceOfferDetail): void {
    const userId = currentProduceUserId();
    if (!userId) return;
    const map = readLocal(userId);
    map[offer.id] = offer;
    appStorage.setJSON(produceScopedKey(PRODUCE_LOCAL_KEY, userId), map);
  },

  removeLocal(id: string): void {
    const userId = currentProduceUserId();
    if (!userId) return;
    const map = readLocal(userId);
    delete map[id];
    appStorage.setJSON(produceScopedKey(PRODUCE_LOCAL_KEY, userId), map);
  },

  clear(): void {
    const userId = currentProduceUserId();
    if (!userId) return;
    appStorage.remove(produceScopedKey(PRODUCE_CACHE_KEY, userId));
    appStorage.remove(produceScopedKey(PRODUCE_LOCAL_KEY, userId));
  },
};

/** Stable cache key for a set of list params (mirrors the backend query). */
export function listCacheKey(params: ProduceListParams, view = 'all'): string {
  return [
    view,
    params.status ?? '',
    params.crop ?? '',
    params.availabilityType ?? '',
    params.category ?? '',
    params.farmId ?? '',
    params.search ?? '',
    params.organicOnly ? 'organic' : '',
    params.page ?? 1,
  ]
    .join('|')
    .toLowerCase();
}
