import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { RefreshControl } from 'react-native';

const mockRefetch = jest.fn();
const mockHistoryRefresh = jest.fn();
const mockFarmRefresh = jest.fn();
let mockFarmId: string | undefined = 'farm-1';
let mockFarmError = false;
let mockFarmLoading = false;
let mockError: { status: number } | null = null;
let mockHistoryError = false;
let mockPending = false;
jest.mock('expo-router', () => ({ useRouter: () => ({ back: jest.fn(), push: jest.fn() }), useLocalSearchParams: () => ({ farmId: mockFarmId }) }));
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/hooks/useAppTheme', () => ({ useAppTheme: () => ({ colors: { primary: 'green' } }) }));
jest.mock('@/components/ui', () => Object.fromEntries(['AgButton','AgEmptyState','AgErrorState','AgScreen','AgSkeleton','AgText','AgOfflineBanner','AgPressable'].map(name => [name, name])));
jest.mock('../components/SoilSamplingMap', () => ({ SoilSamplingMap: 'SamplingMap' }));
jest.mock('../components/SoilFeatureHeader', () => ({ SoilFeatureHeader: 'SoilHeader' }));
jest.mock('../components/SoilHealthCard', () => ({ SoilHealthCard: 'SoilHealthCard' }));
jest.mock('../components/SoilRecommendationCard', () => ({ SoilRecommendationCard: 'SoilRecommendationCard' }));
jest.mock('@/features/weather/components/FarmSelector', () => ({ FarmSelector: 'FarmSelector' }));
jest.mock('@/features/weather', () => ({ useSelectedFarm: () => ({ farms: [], selected: null, select: jest.fn(), isLoading: mockFarmLoading, isError: mockFarmError, refetch: mockFarmRefresh }) }));
jest.mock('../hooks/useSoilSync', () => ({ useSoilSync: jest.fn() }));
jest.mock('../hooks/useSoil', () => ({ useSoilDashboard: () => ({ isLoading: false, refetch: mockRefetch }) }));
jest.mock('../hooks/useSoilScan', () => ({
  useSoilScan: () => ({ isLoading: false, isError: !!mockError, error: mockError, refetch: mockRefetch }),
  useSoilScanHistory: () => ({ isError: mockHistoryError, refetch: mockHistoryRefresh }),
  useRunSoilScan: () => ({ isPending: mockPending, mutate: jest.fn() }),
}));
import { SoilScanScreen } from '../screens/SoilScanScreen';
import { SoilDashboardScreen } from '../screens/SoilDashboardScreen';

let tree: TestRenderer.ReactTestRenderer;
async function mount(screen: React.ReactElement) {
  await act(async () => { tree = TestRenderer.create(screen); });
  return JSON.stringify(tree.toJSON(), (key, value) => key === 'refreshControl' ? undefined : value);
}
beforeEach(() => { jest.clearAllMocks(); mockFarmId = 'farm-1'; mockFarmError = false; mockFarmLoading = false; mockError = null; mockHistoryError = false; mockPending = false; });
afterEach(async () => { await act(async () => tree?.unmount()); });
test('farm errors offer retry instead of claiming there are no farms', async () => {
  mockFarmError = true;
  const output = await mount(<SoilDashboardScreen />);
  expect(output).toContain('AgErrorState');
  expect(output).not.toContain('soil.noFarmTitle');
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockFarmRefresh).toHaveBeenCalled();
});
test('farm loading does not render empty soil readings', async () => {
  mockFarmLoading = true;
  const output = await mount(<SoilDashboardScreen />);
  expect(output).toContain('AgSkeleton');
  expect(output).not.toContain('SoilHealthCard');
});
test('only 404 means no saved scan', async () => {
  mockError = { status: 503 };
  expect(await mount(<SoilScanScreen />)).not.toContain('soil.noSavedScan');
  await act(async () => tree.unmount());
  mockError = { status: 404 };
  expect(await mount(<SoilScanScreen />)).toContain('soil.noSavedScan');
});
test('history error offers its own retry', async () => {
  mockHistoryError = true;
  await mount(<SoilScanScreen />);
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockHistoryRefresh).toHaveBeenCalled();
});
test('refresh reloads saved scan and history without starting a new scan', async () => {
  await mount(<SoilScanScreen />);
  tree.root.findByType(RefreshControl).props.onRefresh();
  expect(mockRefetch).toHaveBeenCalledTimes(1);
  expect(mockHistoryRefresh).toHaveBeenCalledTimes(1);
});
test('refresh does nothing during an active scan', async () => {
  mockPending = true;
  await mount(<SoilScanScreen />);
  tree.root.findByType(RefreshControl).props.onRefresh();
  expect(mockRefetch).not.toHaveBeenCalled();
});
test('missing farm parameter cannot offer a scan mutation', async () => {
  mockFarmId = undefined;
  const output = await mount(<SoilScanScreen />);
  expect(output).toContain('soil.noFarmTitle');
  expect(output).not.toContain('soil.runScan');
});
