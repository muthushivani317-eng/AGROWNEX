import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { marketKeys } from '../constants';
import { getMarketProvider } from '../services/marketProvider';
import { filterCacheKey } from '../services/marketStorage';
import type { AddFavouriteInput, MarketFilters } from '../types';

/** Current mandi prices for a set of filters (docs: crop/market/district/state). */
export function useMarketPrices(filters: MarketFilters, enabled = true) {
  return useQuery({
    queryKey: marketKeys.prices(filterCacheKey(filters)),
    enabled,
    queryFn: () => getMarketProvider().prices(filters),
    // apiClient already retries transient/network/503 failures with bounded
    // backoff. Disable the global React Query retry for this query so one
    // market refresh cannot multiply those upstream requests again.
    retry: false,
    // Prices refresh at most every 15 min (mirrors the backend cache TTL).
    staleTime: 15 * 60 * 1000,
    // The very first fetch for a filter combo not already warmed by the
    // backend's 2-hour favourites cron (e.g. a farmer's own district on the
    // "Nearby" tab) can land before the server's detached background refresh
    // finishes -- it waits up to ~8.5s for that (app/modules/market/service.py
    // -- _ensure_fresh), but a slow-but-successful Agmarknet call can still
    // take a little longer. Rather than leave the farmer looking at a
    // "not found" empty state that a manual pull-to-refresh would have fixed
    // anyway, check once more a few seconds later. Only fires once: after
    // that retry, dataUpdateCount is 2 and this stops.
    refetchInterval: (query) =>
      query.state.dataUpdateCount === 1 && !query.state.error && query.state.data?.items.length === 0
        ? 4000
        : false,
  });
}

/** Live search suggestions for crops, markets, districts and states. */
export function useMarketSearch(term: string) {
  const trimmed = term.trim();
  return useQuery({
    queryKey: marketKeys.search(trimmed.toLowerCase()),
    enabled: trimmed.length > 0,
    queryFn: () => getMarketProvider().search(trimmed),
    staleTime: 5 * 60 * 1000,
  });
}

/** Historical prices for a crop at a market (drives trend charts). */
export function useMarketHistory(
  crop: string | null,
  market: string | null,
  district?: string | null,
) {
  return useQuery({
    queryKey: marketKeys.history(crop ?? '', market ?? ''),
    enabled: Boolean(crop && market),
    queryFn: () =>
      getMarketProvider().history(crop as string, market as string, district),
  });
}

/** The farmer's saved markets, each annotated with the latest known price. */
export function useFavourites() {
  return useQuery({
    queryKey: marketKeys.favourites,
    queryFn: () => getMarketProvider().favourites(),
  });
}

export function useAddFavourite() {
  return useMutation({
    mutationFn: (input: AddFavouriteInput) =>
      getMarketProvider().addFavourite(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: marketKeys.favourites });
    },
  });
}

export function useRemoveFavourite() {
  return useMutation({
    mutationFn: (id: string) => getMarketProvider().removeFavourite(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: marketKeys.favourites });
    },
  });
}
