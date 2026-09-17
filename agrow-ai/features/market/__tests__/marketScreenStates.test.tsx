import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { RefreshControl } from 'react-native';
const mockPricesRefresh = jest.fn();
const mockFavouritesRefresh = jest.fn();
const mockFarmRefresh = jest.fn();
const mockPrices = jest.fn();
let mockFetching = false;
let mockFarmError = false;
let mockFavouriteError = false;
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/components/ui', () => Object.fromEntries(['AgScreen','AgErrorState','AgOfflineBanner'].map(name => [name,name])));
jest.mock('@/features/weather', () => ({ useSelectedFarm: () => ({ selected: null, isLoading: false, isError: mockFarmError, refetch: mockFarmRefresh }) }));
jest.mock('../components/MarketSearchBar', () => ({ MarketSearchBar: 'MarketSearchBar' }));
jest.mock('../components/MarketViewTabs', () => ({ MarketViewTabs: 'MarketViewTabs' }));
jest.mock('../hooks/useMarket', () => ({
  useMarketPrices: (filters: any, enabled: boolean) => { mockPrices(filters, enabled); return { isFetching: mockFetching, refetch: mockPricesRefresh }; },
  useFavourites: () => ({ isError: mockFavouriteError, refetch: mockFavouritesRefresh }),
  useAddFavourite: () => ({ mutate: jest.fn() }),
  useRemoveFavourite: () => ({ mutate: jest.fn() }),
}));
import { MarketScreen } from '../screens/MarketScreen';
let tree: TestRenderer.ReactTestRenderer;
async function mount() { await act(async () => { tree = TestRenderer.create(<MarketScreen />); }); }
beforeEach(() => { jest.clearAllMocks(); mockFetching = mockFarmError = mockFavouriteError = false; });
afterEach(async () => { await act(async () => tree?.unmount()); });
test('refresh does not restart a pending price fetch', async () => {
  mockFetching = true; await mount();
  tree.root.findByType(RefreshControl).props.onRefresh();
  expect(mockPricesRefresh).not.toHaveBeenCalled();
});
test('favourites refresh does not request disabled prices', async () => {
  await mount();
  await act(async () => tree.root.findByType('MarketViewTabs' as any).props.onChange('favourites'));
  tree.root.findByType(RefreshControl).props.onRefresh();
  expect(mockPricesRefresh).not.toHaveBeenCalled();
  expect(mockFavouritesRefresh).toHaveBeenCalled();
});
test('nearby without a district disables unfiltered prices', async () => {
  await mount();
  await act(async () => tree.root.findByType('MarketViewTabs' as any).props.onChange('nearby'));
  expect(mockPrices).toHaveBeenLastCalledWith(expect.anything(), false);
});
test('farm failure in Nearby exposes farm retry', async () => {
  mockFarmError = true; await mount();
  await act(async () => tree.root.findByType('MarketViewTabs' as any).props.onChange('nearby'));
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockFarmRefresh).toHaveBeenCalled();
});
test('favourite lookup errors remain visible on All', async () => {
  mockFavouriteError = true; await mount();
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockFavouritesRefresh).toHaveBeenCalled();
});
