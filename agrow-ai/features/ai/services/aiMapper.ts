import type { SupportedLanguage } from '@/types';

import type {
  ApiChatResponse,
  ApiConversation,
  ApiConversationDetail,
  ApiMessage,
  ChatMessage,
  ChatResult,
  Conversation,
  ConversationDetail,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

const toLang = (value: string): SupportedLanguage => (value === 'en' ? 'en' : 'ta');

/** Keep the farmer greeting consistent for new and previously saved replies. */
export function useAgrowAIGreeting(value: string): string {
  return value.replace(/\bnamaste\b/gi, (match) => {
    if (match === match.toUpperCase()) return 'VANAKKAM';
    return match[0] === match[0].toUpperCase() ? 'Vanakkam' : 'vanakkam';
  });
}

export function apiToMessage(dto: ApiMessage): ChatMessage {
  return {
    id: dto.id,
    sender: dto.sender,
    text: dto.sender === 'assistant' ? useAgrowAIGreeting(dto.message) : dto.message,
    language: toLang(dto.language),
    createdAt: dto.created_at,
  };
}

export function apiToChatResult(dto: ApiChatResponse): ChatResult {
  return {
    conversationId: dto.conversation_id,
    title: dto.title,
    reply: apiToMessage(dto.reply),
  };
}

export function apiToConversation(dto: ApiConversation): Conversation {
  return {
    id: dto.id,
    title: dto.title,
    language: toLang(dto.language),
    lastMessage: dto.last_message,
    messageCount: dto.message_count,
    updatedAt: dto.updated_at,
  };
}

export function apiToConversationDetail(dto: ApiConversationDetail): ConversationDetail {
  return {
    id: dto.id,
    title: dto.title,
    language: toLang(dto.language),
    messages: dto.messages.map(apiToMessage),
  };
}
