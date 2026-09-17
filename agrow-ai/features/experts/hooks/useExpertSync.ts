import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

import { consultationKeys } from '../constants';
import { getExpertProvider } from '../services/expertProvider';
import { consultationOutbox, syncConsultations } from '../services/expertSync';

/**
 * Drains the offline consultation outbox when connectivity returns (docs:
 * OFFLINE → retry, background sync). Mount once on the consultation screens.
 */
export function useExpertSync() {
  const { isConnected } = useNetworkStatus();
  const queryClient = useQueryClient();
  const syncing = useRef(false);

  useEffect(() => {
    if (!isConnected || syncing.current || consultationOutbox.count() === 0) return;
    syncing.current = true;
    void syncConsultations(getExpertProvider())
      .then((result) => {
        if (result.synced > 0) {
          void queryClient.invalidateQueries({ queryKey: consultationKeys.all });
        }
      })
      .finally(() => {
        syncing.current = false;
      });
  }, [isConnected, queryClient]);
}
