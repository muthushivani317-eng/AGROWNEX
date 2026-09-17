import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';
let mockId: string | null = 'a';
let mockDetail: any;
const mockChat = jest.fn();
const mockSetActive = jest.fn();
const mockRefetch = jest.fn();
jest.mock('@/features/weather', () => ({ useSelectedFarm: () => ({ selected: { id: 'farm' } }) }));
jest.mock('@/hooks/useLanguage', () => ({ useLanguage: () => ({ language: 'en' }) }));
jest.mock('@/lib/queryClient', () => ({ queryClient: { invalidateQueries: jest.fn() } }));
jest.mock('../services/aiProvider', () => ({ getAIProvider: () => ({ chat: mockChat }) }));
jest.mock('../services/aiMapper', () => ({ useAgrowAIGreeting: (text: string) => text }));
jest.mock('../store/chatStore', () => ({ useChatStore: (selector: any) => selector({ activeConversationId: mockId, setActive: mockSetActive }) }));
jest.mock('../hooks/useConversations', () => ({ useConversation: () => mockDetail }));
import { useChat } from '../hooks/useChat';
let chat: ReturnType<typeof useChat>;
let tree: TestRenderer.ReactTestRenderer;
function Harness() { chat = useChat(); return null; }
beforeEach(async () => {
  jest.clearAllMocks(); mockId = 'a';
  mockDetail = { data: { messages: [] }, isLoading: false, isError: false, refetch: mockRefetch };
  await act(async () => { tree = TestRenderer.create(<Harness />); });
});
afterEach(async () => { await act(async () => tree.unmount()); });
test('loading and failed history block sending and expose retry', async () => {
  mockDetail = { ...mockDetail, isLoading: true, data: undefined };
  await act(async () => tree.update(<Harness />));
  expect(chat.loadingHistory).toBe(true);
  await act(async () => { await chat.send('hello'); });
  expect(mockChat).not.toHaveBeenCalled();
  mockDetail = { ...mockDetail, isLoading: false, isError: true };
  await act(async () => tree.update(<Harness />));
  expect(chat.historyError).toBe(true);
  chat.retryHistory();
  expect(mockRefetch).toHaveBeenCalled();
});
test('rapid send only submits once and new chat is guarded while pending', async () => {
  let resolve!: (value: any) => void;
  mockChat.mockReturnValue(new Promise(r => { resolve = r; }));
  let pending!: Promise<void>;
  await act(async () => { pending = chat.send('one'); void chat.send('two'); chat.newChat(); });
  expect(mockChat).toHaveBeenCalledTimes(1);
  expect(mockSetActive).not.toHaveBeenCalled();
  await act(async () => { resolve({ conversationId: 'a', reply: { id: 'reply', text: 'done' } }); await pending; });
  expect(chat.isSending).toBe(false);
});
test('a late reply cannot appear in a different selected conversation', async () => {
  let resolve!: (value: any) => void;
  mockChat.mockReturnValue(new Promise(r => { resolve = r; }));
  let pending!: Promise<void>;
  await act(async () => { pending = chat.send('one'); });
  mockId = 'b'; mockDetail = { ...mockDetail, data: undefined, isLoading: true };
  await act(async () => tree.update(<Harness />));
  expect(chat.messages).toHaveLength(0);
  await act(async () => { resolve({ conversationId: 'a', reply: { id: 'reply', text: 'wrong thread' } }); await pending; });
  expect(chat.messages).toHaveLength(0);
});
test('failed send retains a retryable user message and releases pending state', async () => {
  mockChat.mockRejectedValueOnce(new Error('unavailable'));
  await act(async () => { await chat.send('hello'); });
  expect(chat.messages.some(message => message.sendFailed)).toBe(true);
  expect(chat.isSending).toBe(false);
});
