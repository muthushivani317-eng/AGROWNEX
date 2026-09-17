import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { intelligenceKeys } from '../constants';
import { getIntelligenceProvider } from '../services/intelligenceProvider';
import { intelligenceOutbox, syncIntelligence } from '../services/intelligenceSync';

/**
 * Drains the offline intelligence-refresh outbox when connectivity returns (docs:
 * OFFLINE → retry, background sync). Mount once on the intelligence screens.
 */
export function useIntelligenceSync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || intelligenceOutbox.count() === 0) return;
    syncing.current = true;
    void syncIntelligence(getIntelligenceProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: intelligenceKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
