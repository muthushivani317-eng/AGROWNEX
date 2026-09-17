import { appStorage } from '@/lib/storage';

import {
  DEFAULT_PAGE_SIZE,
  NOTIFICATION_CACHE_KEY,
  NOTIFICATION_LOCAL_KEY,
  NOTIFICATION_PREFS_KEY,
} from '../constants';
import type {
  NotificationItem,
  NotificationListParams,
  NotificationPreferences,
} from '../types';

/**
 * Local notification store in MMKV:
 *  - an offline **cache** of the last-seen API lists (keyed by filter) so alerts
 *    stay readable offline,
 *  - the **local-provider** notifications (used in dev / without a backend), and
 *  - a cached copy of the user's **preferences**.
 */
interface ListCache {
  [key: string]: { items: NotificationItem[]; cachedAt: string };
}

function readCache(): ListCache {
  return appStorage.getJSON<ListCache>(NOTIFICATION_CACHE_KEY) ?? {};
}

function readLocal(): Record<string, NotificationItem> {
  return appStorage.getJSON<Record<string, NotificationItem>>(NOTIFICATION_LOCAL_KEY) ?? {};
}

export const notificationStorage = {
  // --- Offline cache (API provider) ---
  cacheList(key: string, items: NotificationItem[]): void {
    const cache = readCache();
    cache[key] = { items, cachedAt: new Date().toISOString() };
    appStorage.setJSON(NOTIFICATION_CACHE_KEY, cache);
  },

  getCachedList(key: string): NotificationItem[] | null {
    return readCache()[key]?.items ?? null;
  },

  // --- Local provider store ---
  localNotifications(): NotificationItem[] {
    return Object.values(readLocal()).sort((a, b) =>
      b.createdAt.localeCompare(a.createdAt),
    );
  },

  hasLocal(): boolean {
    return Object.keys(readLocal()).length > 0;
  },

  getLocal(id: string): NotificationItem | null {
    return readLocal()[id] ?? null;
  },

  upsertLocal(item: NotificationItem): void {
    const map = readLocal();
    map[item.id] = item;
    appStorage.setJSON(NOTIFICATION_LOCAL_KEY, map);
  },

  upsertManyLocal(items: NotificationItem[]): void {
    const map = readLocal();
    items.forEach((item) => {
      map[item.id] = item;
    });
    appStorage.setJSON(NOTIFICATION_LOCAL_KEY, map);
  },

  removeLocal(id: string): void {
    const map = readLocal();
    delete map[id];
    appStorage.setJSON(NOTIFICATION_LOCAL_KEY, map);
  },

  // --- Preferences ---
  getPreferences(): NotificationPreferences | null {
    return appStorage.getJSON<NotificationPreferences>(NOTIFICATION_PREFS_KEY);
  },

  savePreferences(prefs: NotificationPreferences): void {
    appStorage.setJSON(NOTIFICATION_PREFS_KEY, prefs);
  },

  clear(): void {
    appStorage.remove(NOTIFICATION_CACHE_KEY);
    appStorage.remove(NOTIFICATION_LOCAL_KEY);
    appStorage.remove(NOTIFICATION_PREFS_KEY);
  },
};

/** Stable cache key for a set of list params (mirrors the backend query). */
export function listCacheKey(params: NotificationListParams): string {
  return [
    params.module ?? '',
    params.severity ?? '',
    params.unread ? 'unread' : 'all',
    params.page ?? 1,
    params.pageSize ?? DEFAULT_PAGE_SIZE,
  ]
    .join('|')
    .toLowerCase();
}
