import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import type { Paginated } from '@/types';

import type {
  ApiChatResponse,
  ApiConversation,
  ApiConversationDetail,
  ChatInput,
  ChatResult,
  Conversation,
  ConversationDetail,
} from '../types';
import {
  apiToChatResult,
  apiToConversation,
  apiToConversationDetail,
} from './aiMapper';
import type { AIProvider } from './aiProvider';

/** Backend AI provider (docs/API_CONTRACT.md → AI CHAT). Gemini runs server-side. */
export const apiAIProvider: AIProvider = {
  async chat(input: ChatInput): Promise<ChatResult> {
    const dto = await api.post<ApiChatResponse>(endpoints.ai.chat, {
      message: input.message,
      conversation_id: input.conversationId,
      farm_id: input.farmId,
      language: input.language,
    });
    return apiToChatResult(dto);
  },

  async listConversations(): Promise<Conversation[]> {
    const data = await api.get<Paginated<ApiConversation>>(endpoints.ai.history, {
      params: { page: 1, page_size: 50 },
    });
    return data.items.map(apiToConversation);
  },

  async getConversation(id: string): Promise<ConversationDetail> {
    const dto = await api.get<ApiConversationDetail>(endpoints.ai.historyById(id));
    return apiToConversationDetail(dto);
  },

  async deleteConversation(id: string): Promise<void> {
    await api.delete<null>(endpoints.ai.historyById(id));
  },
};
