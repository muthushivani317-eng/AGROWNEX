import { appStorage } from '@/lib/storage';

import { SCHEME_BOOKMARKS_KEY, SCHEME_DOCUMENTS_KEY, SCHEMES_CACHE_KEY } from '../constants';
import type { DocumentType, SchemeSummary } from '../types';

/**
 * Local scheme mirror in MMKV: an offline cache of the last-seen scheme lists
 * (keyed by view/query) so schemes stay readable offline, plus the set of
 * bookmarked scheme ids used by the local provider.
 */
type ListCache = Record<string, { items: SchemeSummary[]; cachedAt: string }>;

function readCache(): ListCache {
  return appStorage.getJSON<ListCache>(SCHEMES_CACHE_KEY) ?? {};
}

function readBookmarks(): string[] {
  return appStorage.getJSON<string[]>(SCHEME_BOOKMARKS_KEY) ?? [];
}

export const schemeStorage = {
  cacheList(key: string, items: SchemeSummary[]): void {
    const cache = readCache();
    cache[key] = { items, cachedAt: new Date().toISOString() };
    appStorage.setJSON(SCHEMES_CACHE_KEY, cache);
  },

  getCachedList(key: string): SchemeSummary[] | null {
    return readCache()[key]?.items ?? null;
  },

  bookmarkIds(): string[] {
    return readBookmarks();
  },

  isBookmarked(id: string): boolean {
    return readBookmarks().includes(id);
  },

  addBookmark(id: string): string[] {
    const list = readBookmarks();
    const next = list.includes(id) ? list : [id, ...list];
    appStorage.setJSON(SCHEME_BOOKMARKS_KEY, next);
    return next;
  },

  removeBookmark(id: string): string[] {
    const next = readBookmarks().filter((b) => b !== id);
    appStorage.setJSON(SCHEME_BOOKMARKS_KEY, next);
    return next;
  },
  documentStates(): Partial<Record<DocumentType, boolean>> {
    return appStorage.getJSON<Partial<Record<DocumentType, boolean>>>(SCHEME_DOCUMENTS_KEY) ?? {};
  },
  setDocument(type: DocumentType, value: boolean): void {
    appStorage.setJSON(SCHEME_DOCUMENTS_KEY, { ...this.documentStates(), [type]: value });
  },

  clear(): void {
    appStorage.remove(SCHEMES_CACHE_KEY);
    appStorage.remove(SCHEME_BOOKMARKS_KEY);
    appStorage.remove(SCHEME_DOCUMENTS_KEY);
  },
};

/** Stable cache key for an eligibility query (mirrors the backend context). */
export function queryCacheKey(query: {
  farmId?: string | null;
  state?: string | null;
  district?: string | null;
  crop?: string | null;
  landHectares?: number | null;
  annualIncome?: number | null;
  farmerCategory?: string | null;
}): string {
  return [
    query.farmId ?? '',
    query.state ?? '',
    query.district ?? '',
    query.crop ?? '',
    query.landHectares ?? '',
    query.annualIncome ?? '',
    query.farmerCategory ?? '',
  ]
    .join('|')
    .toLowerCase();
}

/** Stable cache key for the "all schemes" list filters. */
export function listCacheKey(filters: {
  category?: string | null;
  search?: string | null;
  page?: number;
}): string {
  return [filters.category ?? '', filters.search ?? '', filters.page ?? 1]
    .join('|')
    .toLowerCase();
}
