import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import { organicKeys } from '../constants';
import { getOrganicProvider } from '../services/organicProvider';
import { organicOutbox, syncOrganic } from '../services/organicSync';

/** Replays account-scoped organic mutations once connectivity returns. */
export function useOrganicSync() {
  const { isConnected } = useNetworkStatus(); const client = useQueryClient(); const syncing = useRef(false);
  useEffect(() => {
    if (!isConnected || syncing.current || organicOutbox.count() === 0) return;
    syncing.current = true;
    void syncOrganic(getOrganicProvider()).then((result) => {
      if (result.synced) void client.invalidateQueries({ queryKey: organicKeys.all });
    }).finally(() => { syncing.current = false; });
  }, [client, isConnected]);
}
