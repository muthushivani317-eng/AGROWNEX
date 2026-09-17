import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { ScrollView } from 'react-native';
const mockRefetch = jest.fn().mockResolvedValue({});
const mockFarmRefetch = jest.fn().mockResolvedValue({});
const mockMutate = jest.fn();
let mockFarmError = false;
let mockLoading = false;
let mockHistoryError = false;
let mockCached = false;
jest.mock('expo-router', () => ({ useRouter: () => ({ back: jest.fn(), push: jest.fn() }) }));
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/components/ui', () => Object.fromEntries(['AgButton','AgScreen','AgText'].map(name => [name,name])));
jest.mock('@/features/weather/components/FarmSelector', () => ({ FarmSelector: 'FarmSelector' }));
jest.mock('@/features/weather', () => ({ useSelectedFarm: () => ({ farms: [], selected: mockFarmError ? null : { id: 'f1' }, isError: mockFarmError, isLoading: mockLoading, refetch: mockFarmRefetch, select: jest.fn() }) }));
jest.mock('@/features/farm/hooks/useFarms', () => ({ useFarm: () => ({ data: { crop: 'paddy', sowingDate: '2026-07-01' }, refetch: mockRefetch }) }));
jest.mock('@/features/growth/hooks/useGrowth', () => ({ useGrowthTimeline: () => ({ refetch: mockRefetch }) }));
jest.mock('../hooks/useHarvestReadiness', () => ({
  useHarvestReadiness: () => ({ data: { id: 'r1', state: 'awaiting_farmer_confirmation', cached: mockCached, evidenceObserved: [], missing: [], conflicts: [] }, refetch: mockRefetch }),
  useHarvestReadinessHistory: () => ({ data: [], isError: mockHistoryError, refetch: mockRefetch }),
  useEvaluateHarvestReadiness: () => ({ mutate: mockMutate, reset: jest.fn() }),
  useConfirmHarvestReadiness: () => ({ mutate: mockMutate, reset: jest.fn() }),
}));
import { HarvestReadinessScreen } from '../screens/HarvestReadinessScreen';
let tree: TestRenderer.ReactTestRenderer;
async function mount() { await act(async () => { tree = TestRenderer.create(<HarvestReadinessScreen />); }); }
const buttons = () => tree.root.findAllByType('AgButton' as any);
const text = () => tree.root.findAllByType('AgText' as any).map(x => x.props.children).join(' ');
beforeEach(() => { jest.clearAllMocks(); mockFarmError = mockLoading = mockHistoryError = mockCached = false; });
afterEach(async () => { await act(async () => tree?.unmount()); });

test('loading does not show readiness or setup', async () => {
  mockLoading = true; await mount();
  expect(text()).toContain('harvestReadiness.loadingTitle');
  expect(text()).not.toContain('harvestReadiness.statusLabel');
});
test('farm error retry includes farms', async () => {
  mockFarmError = true; await mount();
  expect(text()).not.toContain('harvestReadiness.noFarmTitle');
  await act(async () => { await buttons().find(x => x.props.title === 'common.retry')!.props.onPress(); });
  expect(mockFarmRefetch).toHaveBeenCalledTimes(1);
});
test('read-only refresh covers all queries and rejects simultaneous refresh', async () => {
  await mount();
  const refresh = tree.root.findByType(ScrollView).props.refreshControl.props.onRefresh;
  await act(async () => { await Promise.all([refresh(), refresh()]); });
  expect(mockFarmRefetch).toHaveBeenCalledTimes(1);
  expect(mockRefetch).toHaveBeenCalledTimes(4);
  expect(mockMutate).not.toHaveBeenCalled();
});
test('history failure has visible retry', async () => {
  mockHistoryError = true; await mount();
  expect(text()).toContain('harvestReadiness.history');
  expect(buttons().some(x => x.props.title === 'common.retry')).toBe(true);
});
test('cached evidence cannot be confirmed', async () => {
  mockCached = true; await mount();
  expect(buttons().some(x => x.props.title === 'harvestReadiness.confirmReady')).toBe(false);
});
test('double assessment press sends only one mutation', async () => {
  await mount();
  const press = buttons().find(x => x.props.title === 'harvestReadiness.check')!.props.onPress;
  await act(async () => { press(); press(); });
  expect(mockMutate).toHaveBeenCalledTimes(1);
});
