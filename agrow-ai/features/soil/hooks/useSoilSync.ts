import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { soilKeys } from '../constants';
import { getSoilProvider } from '../services/soilProvider';
import { soilOutbox, syncSoil } from '../services/soilSync';

/**
 * Drains the offline soil-report outbox when connectivity returns (docs: OFFLINE →
 * retry, background sync). Mount once on the soil screens.
 */
export function useSoilSync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || soilOutbox.count() === 0) return;
    syncing.current = true;
    void syncSoil(getSoilProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: soilKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
