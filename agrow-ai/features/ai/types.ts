import type { SupportedLanguage } from '@/types';

/**
 * AI Chat domain types (docs/API_CONTRACT.md → AI CHAT).
 * Client-side camelCase mirror of the backend AI schemas.
 */

export type Sender = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  sender: Sender;
  text: string;
  language: SupportedLanguage;
  createdAt: string | null;
  /** Local-only: an errored/undelivered assistant turn. */
  error?: boolean;
  errorMessageKey?: 'ai.quotaExceeded' | 'ai.networkError' | 'ai.errorReply';
  sendFailed?: boolean;
}

export interface Conversation {
  id: string;
  title: string | null;
  language: SupportedLanguage;
  lastMessage: string | null;
  messageCount: number;
  updatedAt: string | null;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  language: SupportedLanguage;
  messages: ChatMessage[];
}

export interface ChatInput {
  message: string;
  conversationId?: string;
  farmId?: string;
  language: SupportedLanguage;
}

export interface ChatResult {
  conversationId: string;
  title: string | null;
  reply: ChatMessage;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case) — used by the API provider/mapper.
// --------------------------------------------------------------------------- //
export interface ApiMessage {
  id: string;
  sender: Sender;
  message: string;
  language: string;
  created_at: string | null;
}

export interface ApiChatResponse {
  conversation_id: string;
  title: string | null;
  reply: ApiMessage;
}

export interface ApiConversation {
  id: string;
  title: string | null;
  language: string;
  last_message: string | null;
  message_count: number;
  started_at: string | null;
  updated_at: string | null;
}

export interface ApiConversationDetail {
  id: string;
  title: string | null;
  language: string;
  started_at: string | null;
  messages: ApiMessage[];
}
