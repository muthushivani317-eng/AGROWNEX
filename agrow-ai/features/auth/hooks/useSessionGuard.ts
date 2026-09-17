import { useEffect } from 'react';
import { AppState, type AppStateStatus } from 'react-native';

import { env } from '@/config/env';
import { logger } from '@/lib/logger';

import { useAuthStore } from '../store/authStore';

/**
 * Keeps the authenticated session healthy while the app is in use:
 *  - on foreground, enforces the inactivity timeout (signs out if exceeded);
 *  - proactively refreshes the id token shortly before it expires;
 *  - records activity so the idle window resets.
 *
 * Mounted once near the navigation root.
 */
export function useSessionGuard() {
  const status = useAuthStore((s) => s.status);

  useEffect(() => {
    if (status !== 'authenticated') return;

    const check = async () => {
      const store = useAuthStore.getState();
      const idleFor = Date.now() - store.lastActiveAt;
      if (idleFor > env.sessionIdleTimeoutMs) {
        logger.info('sessionGuard', 'idle timeout — signing out');
        await store.signOut();
        return;
      }
      store.touchActivity();
      await store.refreshSession();
    };

    // Run once on mount, then whenever the app returns to the foreground.
    void check();

    const onChange = (state: AppStateStatus) => {
      if (state === 'active') void check();
    };
    const sub = AppState.addEventListener('change', onChange);

    // Periodic refresh while foregrounded so long sessions stay valid.
    const interval = setInterval(() => {
      void useAuthStore.getState().refreshSession();
    }, env.tokenRefreshLeadMs);

    return () => {
      sub.remove();
      clearInterval(interval);
    };
  }, [status]);
}
