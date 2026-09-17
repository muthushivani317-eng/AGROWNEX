import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { satelliteKeys } from '../constants';
import { getSatelliteProvider } from '../services/satelliteProvider';
import { satelliteOutbox, syncSatellite } from '../services/satelliteSync';

/**
 * Drains the offline satellite refresh outbox when connectivity returns (docs:
 * OFFLINE → retry, background sync). Mount once on the satellite screens.
 */
export function useSatelliteSync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || satelliteOutbox.count() === 0) return;
    syncing.current = true;
    void syncSatellite(getSatelliteProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: satelliteKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
