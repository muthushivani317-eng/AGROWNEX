import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { produceKeys } from '../constants';
import { getProduceProvider } from '../services/produceProvider';
import { produceOutbox, syncProduce } from '../services/produceSync';

/**
 * Drains the offline produce outbox when connectivity returns (docs: OFFLINE →
 * queue synchronization, background sync). Mount once on the Produce List screen.
 */
export function useProduceSync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || produceOutbox.count() === 0) return;
    syncing.current = true;
    void syncProduce(getProduceProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: produceKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
