import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { nutrientKeys } from '../constants';
import { getNutrientProvider } from '../services/nutrientProvider';
import { nutrientOutbox, syncNutrient } from '../services/nutrientSync';

/**
 * Drains the offline nutrient-analysis outbox when connectivity returns (docs:
 * OFFLINE → retry, background sync). Mount once on the nutrient screens.
 */
export function useNutrientSync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || nutrientOutbox.count() === 0) return;
    syncing.current = true;
    void syncNutrient(getNutrientProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: nutrientKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
