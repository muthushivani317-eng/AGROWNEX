import type {
  ApiChatResponse,
  ApiConversation,
  ApiConversationDetail,
} from '../types';
import {
  apiToChatResult,
  apiToConversation,
  apiToConversationDetail,
  useAgrowAIGreeting,
} from '../services/aiMapper';

describe('aiMapper', () => {
  it('maps a chat response', () => {
    const dto: ApiChatResponse = {
      conversation_id: 'c1',
      title: 'Paddy help',
      reply: {
        id: 'm2',
        sender: 'assistant',
        message: 'Try this.',
        language: 'ta',
        created_at: '2026-07-10T09:00:00Z',
      },
    };
    const result = apiToChatResult(dto);
    expect(result.conversationId).toBe('c1');
    expect(result.reply.sender).toBe('assistant');
    expect(result.reply.text).toBe('Try this.');
    expect(result.reply.language).toBe('ta');
  });

  it('uses Vanakkam instead of Namaste in assistant replies', () => {
    expect(useAgrowAIGreeting('Namaste Ruba!')).toBe('Vanakkam Ruba!');
    expect(useAgrowAIGreeting('NAMASTE farmer')).toBe('VANAKKAM farmer');
    expect(useAgrowAIGreeting('The crop is healthy.')).toBe('The crop is healthy.');
  });

  it('maps a conversation summary', () => {
    const dto: ApiConversation = {
      id: 'c1',
      title: 'Cotton',
      language: 'en',
      last_message: 'Use balanced NPK.',
      message_count: 4,
      started_at: '2026-07-10T08:00:00Z',
      updated_at: '2026-07-10T09:00:00Z',
    };
    const conv = apiToConversation(dto);
    expect(conv.title).toBe('Cotton');
    expect(conv.language).toBe('en');
    expect(conv.lastMessage).toBe('Use balanced NPK.');
    expect(conv.messageCount).toBe(4);
  });

  it('maps a conversation detail with messages', () => {
    const dto: ApiConversationDetail = {
      id: 'c1',
      title: null,
      language: 'ta',
      started_at: '2026-07-10T08:00:00Z',
      messages: [
        { id: 'm1', sender: 'user', message: 'Q', language: 'ta', created_at: null },
        { id: 'm2', sender: 'assistant', message: 'A', language: 'ta', created_at: null },
      ],
    };
    const detail = apiToConversationDetail(dto);
    expect(detail.messages).toHaveLength(2);
    expect(detail.messages[0].sender).toBe('user');
    expect(detail.messages[1].text).toBe('A');
  });
});
