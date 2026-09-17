import { useInfiniteQuery, useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { DEFAULT_PAGE_SIZE, notificationKeys } from '../constants';
import { getNotificationProvider } from '../services/notificationProvider';
import { listCacheKey } from '../services/notificationStorage';
import { isOfflineError, notificationOutbox } from '../services/notificationSync';
import type {
  NotificationListParams,
  NotificationPreferences,
  NotificationPreferencesPatch,
} from '../types';

const LIST_STALE = 60 * 1000;

export function useNotificationList(params: NotificationListParams, enabled = true) {
  return useInfiniteQuery({
    queryKey: notificationKeys.list(listCacheKey(params)),
    enabled,
    initialPageParam: params.page ?? 1,
    queryFn: ({ pageParam }) =>
      getNotificationProvider().list({
        pageSize: DEFAULT_PAGE_SIZE,
        ...params,
        page: pageParam,
      }),
    getNextPageParam: (lastPage) =>
      lastPage.page < lastPage.totalPages ? lastPage.page + 1 : undefined,
    staleTime: LIST_STALE,
  });
}

export function useUnreadCount(enabled = true) {
  return useQuery({
    queryKey: notificationKeys.unread,
    enabled,
    queryFn: () => getNotificationProvider().unread(),
    staleTime: LIST_STALE,
    refetchInterval: 5 * 60 * 1000, // keep the badge fresh in the background
  });
}

export function useNotificationPreferences(enabled = true) {
  return useQuery({
    queryKey: notificationKeys.preferences,
    enabled,
    queryFn: () => getNotificationProvider().getPreferences(),
  });
}

function invalidateAll(): void {
  void queryClient.invalidateQueries({ queryKey: notificationKeys.all });
}

export interface MutationResult {
  offline: boolean;
}

export function useMarkRead() {
  return useMutation<MutationResult, unknown, string>({
    mutationFn: async (id) => {
      try {
        await getNotificationProvider().markRead(id);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          notificationOutbox.enqueue({ op: 'read', notificationId: id });
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: invalidateAll,
  });
}

export function useMarkAllRead() {
  return useMutation<MutationResult, unknown, void>({
    mutationFn: async () => {
      try {
        await getNotificationProvider().markAllRead();
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          notificationOutbox.enqueue({ op: 'readAll' });
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: invalidateAll,
  });
}

export function useDismissNotification() {
  return useMutation<MutationResult, unknown, string>({
    mutationFn: async (id) => {
      try {
        await getNotificationProvider().dismiss(id);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          notificationOutbox.enqueue({ op: 'dismiss', notificationId: id });
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: invalidateAll,
  });
}

export function useUpdatePreferences() {
  return useMutation<NotificationPreferences, unknown, NotificationPreferencesPatch>({
    mutationFn: (patch) => getNotificationProvider().updatePreferences(patch),
    onSuccess: (prefs) => {
      queryClient.setQueryData(notificationKeys.preferences, prefs);
      invalidateAll();
    },
  });
}
