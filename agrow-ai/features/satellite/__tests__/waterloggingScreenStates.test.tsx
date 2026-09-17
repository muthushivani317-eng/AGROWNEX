import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { RefreshControl } from 'react-native';

const mockLatest = jest.fn();
const mockHistory = jest.fn();
const mockDashboard = jest.fn();
const mockFarms = jest.fn();
const mockMutate = jest.fn();
let mockFarmError = false;
let mockLoading = false;
let mockHistoryError = false;
let mockLatestError = false;
let mockPending = false;
let mockData: any;
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/components/ui', () => Object.fromEntries(['AgButton', 'AgCard', 'AgErrorState', 'AgOfflineBanner', 'AgScreen', 'AgSkeleton', 'AgText'].map(name => [name, name])));
jest.mock('../components/SatelliteBackHeader', () => ({ SatelliteBackHeader: 'SatelliteBackHeader' }));
jest.mock('../components/LatestImageCard', () => ({ LatestImageCard: 'LatestImageCard' }));
jest.mock('../components/SatelliteImageViewer', () => ({ SatelliteImageViewer: 'SatelliteImageViewer' }));
jest.mock('@/features/weather/components/FarmSelector', () => ({ FarmSelector: 'FarmSelector' }));
jest.mock('@/features/weather', () => ({ useSelectedFarm: () => ({ farms: [], selected: { id: 'farm-1', hasBoundary: true }, select: jest.fn(), isError: mockFarmError, isLoading: mockLoading, refetch: mockFarms }) }));
jest.mock('../hooks/useSatellite', () => ({
  useWaterloggingAssessment: () => ({ data: mockData, isError: mockLatestError, refetch: mockLatest }),
  useWaterloggingHistory: () => ({ isError: mockHistoryError, refetch: mockHistory }),
  useSatelliteDashboard: () => ({ refetch: mockDashboard }),
  useRefreshWaterlogging: () => ({ isPending: mockPending, mutate: mockMutate }),
}));
import { WaterloggingScreen } from '../screens/WaterloggingScreen';

let tree: TestRenderer.ReactTestRenderer;
async function mount() {
  await act(async () => { tree = TestRenderer.create(<WaterloggingScreen />); });
  return JSON.stringify(tree.toJSON(), (key, value) => ['refreshControl', '_owner'].includes(key) ? undefined : value);
}
beforeEach(() => {
  jest.clearAllMocks();
  mockFarmError = mockLoading = mockHistoryError = mockLatestError = mockPending = false;
  mockData = undefined;
});
afterEach(async () => { await act(async () => tree?.unmount()); });
test('farm failure offers retry rather than a missing-farm message', async () => {
  mockFarmError = true;
  const output = await mount();
  expect(output).not.toContain('satellite.waterlogging.selectFarm');
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockFarms).toHaveBeenCalledTimes(1);
});
test('initial farm loading shows skeletons instead of an assessment', async () => {
  mockLoading = true;
  expect(await mount()).toContain('AgSkeleton');
});
test('pull refresh reloads all saved sources without requesting new analysis', async () => {
  await mount();
  tree.root.findByType(RefreshControl).props.onRefresh();
  for (const refetch of [mockFarms, mockLatest, mockHistory, mockDashboard]) expect(refetch).toHaveBeenCalledTimes(1);
  expect(mockMutate).not.toHaveBeenCalled();
});
test('pending analysis prevents duplicate refresh', async () => {
  mockPending = true;
  await mount();
  tree.root.findByType(RefreshControl).props.onRefresh();
  const button = tree.root.findAllByType('AgButton' as any).find(node => node.props.title === 'satellite.waterlogging.refresh')!;
  button.props.onPress();
  expect(mockLatest).not.toHaveBeenCalled();
  expect(mockMutate).not.toHaveBeenCalled();
});
test('history failure exposes independent retry', async () => {
  mockHistoryError = true;
  await mount();
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockHistory).toHaveBeenCalledTimes(1);
});
test('stale results are explicitly labelled', async () => {
  mockData = { decision: 'no_surface_water_increase', freshness: 'stale', provenance: {}, evidencePresent: [], evidenceMissing: [], createdAt: '2026-08-29T00:00:00Z' };
  expect(await mount()).toContain('satellite.waterlogging.stale');
});
test('failed latest fetch cannot present cached result as current', async () => {
  mockLatestError = true;
  mockData = { decision: 'no_surface_water_increase' };
  const output = await mount();
  expect(output).toContain('satellite.waterlogging.error');
  expect(output).not.toContain('satellite.waterlogging.no_surface_water_increase');
});
