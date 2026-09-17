import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import { FlatList } from 'react-native';
const mockRefetch = jest.fn();
let mockLoading = false;
let mockError = false;
jest.mock('expo-router', () => ({ useRouter: () => ({ back: jest.fn() }) }));
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('@/hooks/useAppTheme', () => ({ useAppTheme: () => ({ colors: { primary: '#008800' } }) }));
jest.mock('@/components/ui', () => Object.fromEntries(['AgCard','AgEmptyState','AgErrorState','AgPressable','AgScreen','AgSkeleton','AgText'].map(name => [name,name])));
jest.mock('../hooks/useConversations', () => ({
  useConversations: () => ({ data: [], isLoading: mockLoading, isError: mockError, isRefetching: false, refetch: mockRefetch }),
  useDeleteConversation: () => ({ isPending: false, mutate: jest.fn() }),
}));
import { HistoryScreen } from '../screens/HistoryScreen';
let tree: TestRenderer.ReactTestRenderer;
async function mount() { await act(async () => { tree = TestRenderer.create(<HistoryScreen />); }); }
beforeEach(() => { jest.clearAllMocks(); mockLoading = mockError = false; });
afterEach(async () => { await act(async () => tree?.unmount()); });
test('initial loading uses visible skeleton dimensions', async () => {
  mockLoading = true; await mount();
  expect(tree.root.findAllByType('AgSkeleton' as any)[0].props.style.height).toBe(64);
});
test('history failure exposes retry', async () => {
  mockError = true; await mount();
  tree.root.findByType('AgErrorState' as any).props.onRetry();
  expect(mockRefetch).toHaveBeenCalledTimes(1);
});
test('empty history supports pull refresh', async () => {
  await mount();
  tree.root.findByType(FlatList).props.onRefresh();
  expect(mockRefetch).toHaveBeenCalledTimes(1);
});
