import { uuid } from '@/utils/id';

import type {
  ChatInput,
  ChatMessage,
  ChatResult,
  Conversation,
  ConversationDetail,
} from '../types';
import { AIError, type AIProvider } from './aiProvider';
import { aiStorage, type StoredConversation } from './aiStorage';
import { deriveTitle, generateMockReply } from './mockReply';

/**
 * Offline-first AI provider. Persists conversations in MMKV and answers with the
 * deterministic mock reply — so the assistant and history work in development
 * without a backend or Gemini key.
 */
function toSummary(conversation: StoredConversation): Conversation {
  const last = conversation.messages[conversation.messages.length - 1];
  return {
    id: conversation.id,
    title: conversation.title,
    language: conversation.language,
    lastMessage: last ? last.text : null,
    messageCount: conversation.messages.length,
    updatedAt: conversation.updatedAt,
  };
}

export const localAIProvider: AIProvider = {
  async chat(input: ChatInput): Promise<ChatResult> {
    const existing = input.conversationId
      ? aiStorage.get(input.conversationId)
      : null;
    const conversation: StoredConversation = existing ?? {
      id: uuid(),
      title: null,
      language: input.language,
      messages: [],
      updatedAt: new Date().toISOString(),
    };

    const now = new Date().toISOString();
    const userMessage: ChatMessage = {
      id: uuid(),
      sender: 'user',
      text: input.message.trim(),
      language: input.language,
      createdAt: now,
    };
    const replyAt = new Date().toISOString();
    const reply: ChatMessage = {
      id: uuid(),
      sender: 'assistant',
      text: generateMockReply(input.message, input.language),
      language: input.language,
      createdAt: replyAt,
    };

    conversation.messages = [...conversation.messages, userMessage, reply];
    conversation.title = conversation.title ?? deriveTitle(input.message, input.language);
    conversation.language = input.language;
    conversation.updatedAt = replyAt;
    aiStorage.upsert(conversation);

    return { conversationId: conversation.id, title: conversation.title, reply };
  },

  async listConversations(): Promise<Conversation[]> {
    return aiStorage
      .all()
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
      .map(toSummary);
  },

  async getConversation(id: string): Promise<ConversationDetail> {
    const conversation = aiStorage.get(id);
    if (!conversation) throw new AIError('not_found', 'Conversation not found');
    return {
      id: conversation.id,
      title: conversation.title,
      language: conversation.language,
      messages: conversation.messages,
    };
  },

  async deleteConversation(id: string): Promise<void> {
    aiStorage.remove(id);
  },
};
