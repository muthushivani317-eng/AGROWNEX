import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { notificationKeys } from '../constants';
import { getNotificationProvider } from '../services/notificationProvider';
import { notificationOutbox, syncNotifications } from '../services/notificationSync';

/**
 * Drains the offline notification outbox when connectivity returns (docs:
 * OFFLINE → retry, background sync). Mount once on the Notification Center.
 */
export function useNotificationSync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || notificationOutbox.count() === 0) return;
    syncing.current = true;
    void syncNotifications(getNotificationProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: notificationKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
