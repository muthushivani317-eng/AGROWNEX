import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { FlatList } from 'react-native';
const mockRefetch = jest.fn();
const mockFarms = jest.fn();
let mockFarmError = false;
let mockLoading = false;
let mockError = false;
jest.mock('expo-router', () => ({ useRouter: () => ({ back: jest.fn(), push: jest.fn() }) }));
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/hooks/useAppTheme', () => ({ useAppTheme: () => ({ colors: { primary: '#008800' } }) }));
jest.mock('@/components/ui', () => Object.fromEntries(['AgCard','AgEmptyState','AgErrorState','AgPressable','AgScreen','AgSkeleton','AgText'].map(name => [name,name])));
jest.mock('@/features/weather', () => ({ useSelectedFarm: () => ({ farms: [], selected: null, isError: mockFarmError, isLoading: mockLoading, refetch: mockFarms }) }));
jest.mock('../hooks/useDisease', () => ({ useDiseaseHistory: () => ({ data: [], isLoading: false, isError: mockError, isRefetching: false, refetch: mockRefetch }) }));
import { DiseaseHistoryScreen } from '../screens/DiseaseHistoryScreen';
let tree: TestRenderer.ReactTestRenderer;
async function mount() { await act(async () => { tree = TestRenderer.create(<DiseaseHistoryScreen />); }); }
beforeEach(() => { jest.clearAllMocks(); mockFarmError = mockLoading = mockError = false; });
afterEach(async () => { await act(async () => tree?.unmount()); });
test('farm failure offers farm retry instead of empty history', async () => {
  mockFarmError = true; await mount();
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockFarms).toHaveBeenCalledTimes(1);
  expect(tree.root.findAllByType(FlatList)).toHaveLength(0);
});
test('farm loading shows dimensioned skeletons', async () => {
  mockLoading = true; await mount();
  expect(tree.root.findAllByType('AgSkeleton' as any)[0].props.style.height).toBe(80);
});
test('history failure offers history retry', async () => {
  mockError = true; await mount();
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockRefetch).toHaveBeenCalledTimes(1);
});
test('empty history still supports pull refresh', async () => {
  await mount();
  tree.root.findByType(FlatList).props.onRefresh();
  expect(mockRefetch).toHaveBeenCalledTimes(1);
  expect(mockFarms).toHaveBeenCalledTimes(1);
});
