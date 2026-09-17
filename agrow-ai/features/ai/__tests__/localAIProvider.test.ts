// Deterministic, unique ids (the global expo-crypto mock returns a fixed UUID).
jest.mock('@/utils/id', () => {
  let n = 0;
  return { uuid: () => `id-${++n}` };
});

import { localAIProvider } from '../services/localAIProvider';
import { aiStorage } from '../services/aiStorage';

describe('localAIProvider', () => {
  beforeEach(() => aiStorage.clear());

  it('starts a conversation and persists both turns', async () => {
    const result = await localAIProvider.chat({
      message: 'How to grow paddy?',
      language: 'ta',
    });
    expect(result.conversationId).toBeTruthy();
    expect(result.reply.sender).toBe('assistant');
    expect(result.reply.text).toContain('டெமோ பதில்');

    const detail = await localAIProvider.getConversation(result.conversationId);
    expect(detail.messages.map((m) => m.sender)).toEqual(['user', 'assistant']);
    expect(detail.title).toBe('How to grow paddy?');
  });

  it('continues an existing conversation', async () => {
    const first = await localAIProvider.chat({ message: 'One', language: 'en' });
    await localAIProvider.chat({
      message: 'Two',
      conversationId: first.conversationId,
      language: 'en',
    });
    const detail = await localAIProvider.getConversation(first.conversationId);
    expect(detail.messages).toHaveLength(4);
    expect(detail.messages.map((m) => m.text)).toContain('Two');
  });

  it('lists conversations newest-first and deletes them', async () => {
    const a = await localAIProvider.chat({ message: 'Alpha', language: 'en' });
    const b = await localAIProvider.chat({ message: 'Beta', language: 'en' });

    const list = await localAIProvider.listConversations();
    expect(list).toHaveLength(2);
    expect(list[0].id).toBe(b.conversationId); // most recent first

    await localAIProvider.deleteConversation(a.conversationId);
    const after = await localAIProvider.listConversations();
    expect(after.map((c) => c.id)).toEqual([b.conversationId]);
  });

  it('throws for an unknown conversation', async () => {
    await expect(localAIProvider.getConversation('missing')).rejects.toThrow();
  });
});
