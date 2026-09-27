import { useEffect, useState } from 'react';
import { getConfig } from './config';

export type MarketplaceAttention = {
  new_suppliers: number;
  new_batches: number;
  offers_accepted: number;
  total: number;
};

const MARKETPLACE_PERMISSIONS = [
  'manage_marketplace_qc',
  'manage_marketplace_suppliers',
  'manage_marketplace_procurement',
];

/**
 * Polls what needs an admin in the Organic Inputs marketplace (new seller
 * applications, new batches offered, accepted purchase offers). Drives the
 * menu badge and the alert banner. Plain JSON endpoint (no envelope).
 */
export function useMarketplaceAttention(permissions: string[], intervalMs = 60_000) {
  const allowed = permissions.some((p) => MARKETPLACE_PERMISSIONS.includes(p));
  const [data, setData] = useState<MarketplaceAttention | null>(null);
  useEffect(() => {
    if (!allowed) return;
    let active = true;
    const load = async () => {
      try {
        const response = await fetch(`${getConfig().apiBaseUrl}/admin/organic-inputs/attention`, {
          credentials: 'include',
          cache: 'no-store',
        });
        if (response.ok && active) setData((await response.json()) as MarketplaceAttention);
      } catch {
        // Badge is best-effort; the page itself still works.
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), intervalMs);
    return () => { active = false; window.clearInterval(timer); };
  }, [allowed, intervalMs]);
  return data;
}
