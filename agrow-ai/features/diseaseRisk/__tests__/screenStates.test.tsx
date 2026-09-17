import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { ScrollView } from 'react-native';
import { ApiError } from '@/types';
const mockRefetch = jest.fn().mockResolvedValue({});
const mockFarmRefetch = jest.fn().mockResolvedValue({});
let mockFarmError = false;
let mockGrowthError = false;
let mockHistoryError = false;
let mockGrowthFailure: unknown;
jest.mock('expo-router', () => ({ useRouter: () => ({ back: jest.fn(), push: jest.fn() }) }));
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/components/ui', () => Object.fromEntries(['AgButton','AgScreen','AgText'].map(name => [name,name])));
jest.mock('@/features/weather/components/FarmSelector', () => ({ FarmSelector: 'FarmSelector' }));
jest.mock('@/features/weather', () => ({ useSelectedFarm: () => ({ farms: [], selected: mockFarmError ? null : { id: 'f1' }, isError: mockFarmError, isLoading: false, refetch: mockFarmRefetch, select: jest.fn() }) }));
jest.mock('@/features/growth', () => ({ useGrowthTimeline: () => ({ isLoading: false, isError: mockGrowthError, error: mockGrowthFailure, refetch: mockRefetch }) }));
jest.mock('../api', () => ({ evaluateRisk: jest.fn(), getCurrentRisk: jest.fn(), getRiskHistory: jest.fn() }));
jest.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryKey }: any) => ({ data: queryKey[1] === 'history' ? [] : null, isLoading: false, isError: queryKey[1] === 'history' && mockHistoryError, refetch: mockRefetch }),
  useMutation: () => ({ isPending: false, mutate: jest.fn(), reset: jest.fn() }),
}));
import { DiseaseRiskScreen } from '../DiseaseRiskScreen';
let tree: TestRenderer.ReactTestRenderer;
async function mount() { await act(async () => { tree = TestRenderer.create(<DiseaseRiskScreen />); }); }
beforeEach(() => { jest.clearAllMocks(); mockFarmError = mockGrowthError = mockHistoryError = false; mockGrowthFailure = undefined; });
afterEach(async () => { await act(async () => tree?.unmount()); });
const text = () => tree.root.findAllByType('AgText' as any).map(x => x.props.children).join(' ') + tree.root.findAllByType('AgButton' as any).map(x => x.props.title).join(' ');
test('farm failure is not presented as no farms and retry reloads farms', async () => {
  mockFarmError = true; await mount();
  expect(text()).not.toContain('diseaseRisk.noFarmTitle');
  await act(async () => { await tree.root.findAllByType('AgButton' as any).find(x => x.props.title === 'common.retry')!.props.onPress(); });
  expect(mockFarmRefetch).toHaveBeenCalledTimes(1);
  expect(mockRefetch).not.toHaveBeenCalled();
});
test('growth failure does not claim a growth record is missing', async () => {
  mockGrowthError = true; await mount();
  expect(text()).not.toContain('diseaseRisk.noCropCycle');
  expect(text()).toContain('diseaseRisk.errors.server');
});
test('history failure exposes retry', async () => {
  mockHistoryError = true; await mount();
  expect(text()).toContain('diseaseRisk.history');
  expect(text()).toContain('common.retry');
});
test('a missing growth session is a prerequisite, not a service error', async () => {
  mockGrowthError = true;
  mockGrowthFailure = new ApiError({ status: 404, errorCode: 'growth_session_not_found', message: 'Missing' });
  await mount();
  expect(text()).toContain('diseaseRisk.noCropCycle');
  expect(text()).not.toContain('diseaseRisk.errors.server');
});
test('pull refresh reloads farms, current, history and growth without evaluation', async () => {
  await mount();
  await act(async () => { tree.root.findByType(ScrollView).props.refreshControl.props.onRefresh(); });
  expect(mockFarmRefetch).toHaveBeenCalledTimes(1);
  expect(mockRefetch).toHaveBeenCalledTimes(3);
});
