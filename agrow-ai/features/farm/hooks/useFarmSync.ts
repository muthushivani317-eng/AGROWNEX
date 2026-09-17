import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { farmKeys } from '../constants';
import { getFarmProvider } from '../services/farmProvider';
import { farmOutbox, syncFarms } from '../services/farmSync';

/**
 * Drains the offline farm outbox when connectivity returns (docs: OFFLINE →
 * queue synchronization). Mount once on the Farm List screen.
 */
export function useFarmSync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || farmOutbox.count() === 0) return;
    syncing.current = true;
    void syncFarms(getFarmProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: farmKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
