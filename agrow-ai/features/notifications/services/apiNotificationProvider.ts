import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError, type Paginated } from '@/types';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  ApiMarkReadResult,
  ApiNotification,
  ApiNotificationPreferences,
  ApiUnreadCount,
  NotificationItem,
  NotificationListParams,
  NotificationListResult,
  NotificationPreferences,
  NotificationPreferencesPatch,
} from '../types';
import {
  apiToListResult,
  apiToNotification,
  apiToPreferences,
  DEFAULT_PREFERENCES,
  preferencesPatchToApi,
} from './notificationMapper';
import type { NotificationProvider } from './notificationProvider';
import { listCacheKey, notificationStorage } from './notificationStorage';

/**
 * Backend notification provider (docs/API_CONTRACT.md → NOTIFICATIONS). Every
 * successful list/unread/preferences fetch is mirrored to MMKV so alerts stay
 * readable offline; on a network error the last cached copy is served instead of
 * erroring. Read/dismiss mutations that fail offline surface the network error so
 * the hook can queue them in the retry outbox.
 */
function cachedListFallback(key: string, err: unknown): NotificationListResult {
  const cached = notificationStorage.getCachedList(key);
  if (cached && err instanceof ApiError && err.isNetwork) {
    return {
      items: cached,
      page: 1,
      pageSize: cached.length,
      total: cached.length,
      totalPages: 1,
      cached: true,
    };
  }
  throw err;
}

export const apiNotificationProvider: NotificationProvider = {
  async list(params: NotificationListParams): Promise<NotificationListResult> {
    const key = listCacheKey(params);
    try {
      const dto = await api.get<Paginated<ApiNotification>>(endpoints.notifications.root, {
        params: {
          module: params.module ?? undefined,
          severity: params.severity ?? undefined,
          unread: params.unread ?? undefined,
          page: params.page ?? 1,
          page_size: params.pageSize ?? DEFAULT_PAGE_SIZE,
        },
      });
      const result = apiToListResult(dto);
      if (result.page === 1) notificationStorage.cacheList(key, result.items);
      return result;
    } catch (err) {
      return cachedListFallback(key, err);
    }
  },

  async unread(): Promise<number> {
    try {
      const dto = await api.get<ApiUnreadCount>(endpoints.notifications.unread);
      return dto.unread;
    } catch (err) {
      if (err instanceof ApiError && err.isNetwork) {
        // Fall back to counting the cached "all" list.
        const cached = notificationStorage.getCachedList(listCacheKey({}));
        return cached ? cached.filter((n) => !n.read).length : 0;
      }
      throw err;
    }
  },

  async markRead(id: string): Promise<NotificationItem> {
    return apiToNotification(
      await api.put<ApiNotification>(endpoints.notifications.read(id)),
    );
  },

  async markAllRead(): Promise<number> {
    const dto = await api.put<ApiMarkReadResult>(endpoints.notifications.readAll);
    return dto.updated;
  },

  async dismiss(id: string): Promise<void> {
    await api.delete<null>(endpoints.notifications.byId(id));
  },

  async getPreferences(): Promise<NotificationPreferences> {
    try {
      const prefs = apiToPreferences(
        await api.get<ApiNotificationPreferences>(endpoints.notifications.preferences),
      );
      notificationStorage.savePreferences(prefs);
      return prefs;
    } catch (err) {
      if (err instanceof ApiError && err.isNetwork) {
        return notificationStorage.getPreferences() ?? DEFAULT_PREFERENCES;
      }
      throw err;
    }
  },

  async updatePreferences(
    patch: NotificationPreferencesPatch,
  ): Promise<NotificationPreferences> {
    const prefs = apiToPreferences(
      await api.put<ApiNotificationPreferences>(
        endpoints.notifications.preferences,
        preferencesPatchToApi(patch),
      ),
    );
    notificationStorage.savePreferences(prefs);
    return prefs;
  },
};
