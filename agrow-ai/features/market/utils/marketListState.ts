import type { MarketView } from '../types';

type ListStateInput = {
  loading: boolean;
  error: boolean;
  nearbyBlocked: boolean;
  view: MarketView;
};

type LoadingState = { kind: 'loading' };
type MessageState = {
  kind: 'unavailable' | 'nearby' | 'favourites' | 'empty';
  titleKey: string;
  messageKey: string;
  canRetry: boolean;
};

export type MarketListState = LoadingState | MessageState;

type DataNoticeInput = {
  error: boolean;
  itemCount: number;
  view: MarketView;
};

export type MarketDataNotice = {
  kind: 'last-verified';
  titleKey: string;
  messageKey: string;
  canRetry: true;
};

/**
 * Keeps transport/provider failures separate from a valid empty market query.
 * This state is shared by the screen and tests so outage copy cannot regress
 * into the "No prices found" state again.
 */
export function resolveMarketListState({
  loading,
  error,
  nearbyBlocked,
  view,
}: ListStateInput): MarketListState {
  if (loading) return { kind: 'loading' };
  if (error) {
    return {
      kind: 'unavailable',
      titleKey: 'market.unavailableTitle',
      messageKey: 'market.providerUnavailable',
      canRetry: true,
    };
  }
  if (nearbyBlocked) {
    return {
      kind: 'nearby',
      titleKey: 'market.nearbyNoFarmTitle',
      messageKey: 'market.nearbyNoFarmMessage',
      canRetry: false,
    };
  }
  if (view === 'favourites') {
    return {
      kind: 'favourites',
      titleKey: 'market.favouritesEmptyTitle',
      messageKey: 'market.favouritesEmptyMessage',
      canRetry: false,
    };
  }
  return {
    kind: 'empty',
    titleKey: 'market.emptyTitle',
    messageKey: 'market.emptyMessage',
    canRetry: false,
  };
}

/**
 * React Query intentionally retains the last successful rows when a refetch
 * fails. Surface that current failure without removing useful verified data.
 */
export function resolveMarketDataNotice({
  error,
  itemCount,
  view,
}: DataNoticeInput): MarketDataNotice | null {
  if (!error || itemCount === 0 || view === 'favourites') return null;
  return {
    kind: 'last-verified',
    titleKey: 'market.lastVerifiedTitle',
    messageKey: 'market.lastVerifiedMessage',
    canRetry: true,
  };
}
