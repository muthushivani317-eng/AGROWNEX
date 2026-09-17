import { en } from '@/localization/locales/en';
import { ta } from '@/localization/locales/ta';

import {
  resolveMarketDataNotice,
  resolveMarketListState,
} from '../utils/marketListState';

describe('market list states', () => {
  it('maps an API/provider failure to one actionable unavailable state', () => {
    expect(
      resolveMarketListState({
        loading: false,
        error: true,
        nearbyBlocked: false,
        view: 'all',
      }),
    ).toEqual({
      kind: 'unavailable',
      titleKey: 'market.unavailableTitle',
      messageKey: 'market.providerUnavailable',
      canRetry: true,
    });
  });

  it('maps a genuine successful empty response to No prices found', () => {
    expect(
      resolveMarketListState({
        loading: false,
        error: false,
        nearbyBlocked: false,
        view: 'all',
      }),
    ).toEqual({
      kind: 'empty',
      titleKey: 'market.emptyTitle',
      messageKey: 'market.emptyMessage',
      canRetry: false,
    });
  });

  it('provides English and Tamil copy for the unavailable state', () => {
    expect(en.market.unavailableTitle).toBeTruthy();
    expect(en.market.providerUnavailable).toContain('temporarily unavailable');
    expect(ta.market.unavailableTitle).toBeTruthy();
    expect(ta.market.providerUnavailable).not.toBe(en.market.providerUnavailable);
  });

  it('surfaces a current refresh failure when verified rows are retained', () => {
    expect(
      resolveMarketDataNotice({ error: true, itemCount: 2, view: 'all' }),
    ).toEqual({
      kind: 'last-verified',
      titleKey: 'market.lastVerifiedTitle',
      messageKey: 'market.lastVerifiedMessage',
      canRetry: true,
    });
  });

  it('does not show the retained-data banner without rows or on favourites', () => {
    expect(
      resolveMarketDataNotice({ error: true, itemCount: 0, view: 'all' }),
    ).toBeNull();
    expect(
      resolveMarketDataNotice({
        error: true,
        itemCount: 2,
        view: 'favourites',
      }),
    ).toBeNull();
  });

  it('localizes the last-verified outage notice in English and Tamil', () => {
    expect(en.market.lastVerifiedTitle).toBeTruthy();
    expect(en.market.lastVerifiedMessage).toContain('last verified');
    expect(ta.market.lastVerifiedTitle).toBeTruthy();
    expect(ta.market.lastVerifiedMessage).not.toBe(
      en.market.lastVerifiedMessage,
    );
  });
});
