import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { memoryKeys } from '../constants';
import { getMemoryProvider } from '../services/memoryProvider';
import { memoryOutbox, syncMemory } from '../services/memorySync';

/**
 * Drains the offline memory-rebuild outbox when connectivity returns (docs: OFFLINE →
 * retry, background sync). Mount once on the memory screens.
 */
export function useMemorySync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || memoryOutbox.count() === 0) return;
    syncing.current = true;
    void syncMemory(getMemoryProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: memoryKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
