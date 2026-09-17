import { useEffect, useState } from 'react';
import { AppState } from 'react-native';

/**
 * Lightweight connectivity probe. We avoid a native NetInfo dependency by
 * pinging a fast, cache-busted endpoint and re-checking when the app returns to
 * the foreground. Good enough to drive offline banners and retry affordances;
 * the offline queue (lib/db) provides durable sync.
 */
async function ping(signal: AbortSignal): Promise<boolean> {
  try {
    const res = await fetch('https://clients3.google.com/generate_204', {
      method: 'GET',
      signal,
      cache: 'no-store',
    });
    return res.status === 204 || res.ok;
  } catch {
    return false;
  }
}

export function useNetworkStatus() {
  const [isConnected, setIsConnected] = useState(true);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    let mounted = true;
    let activeController: AbortController | null = null;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    let inFlight = false;

    const check = async () => {
      if (!mounted || inFlight) return;
      inFlight = true;
      const controller = new AbortController();
      activeController = controller;
      // A stalled connection must not keep the offline state pending forever.
      timeout = setTimeout(() => controller.abort(), 8_000);
      setChecking(true);
      const ok = await ping(controller.signal);
      clearTimeout(timeout);
      activeController = null;
      inFlight = false;
      if (mounted) {
        setIsConnected(ok);
        setChecking(false);
      }
    };

    check();
    const interval = setInterval(check, 20_000);
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') check();
    });

    return () => {
      mounted = false;
      activeController?.abort();
      clearTimeout(timeout);
      clearInterval(interval);
      sub.remove();
    };
  }, []);

  return { isConnected, checking };
}
