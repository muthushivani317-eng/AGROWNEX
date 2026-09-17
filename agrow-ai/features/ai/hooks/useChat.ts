import { useCallback, useEffect, useRef, useState } from 'react';

import { useSelectedFarm } from '@/features/weather';
import { queryClient } from '@/lib/queryClient';
import { useLanguage } from '@/hooks/useLanguage';
import { uuid } from '@/utils/id';
import { ApiError } from '@/types';

import { aiKeys } from '../constants';
import { getAIProvider } from '../services/aiProvider';
import { useAgrowAIGreeting } from '../services/aiMapper';
import { useChatStore } from '../store/chatStore';
import type { ChatMessage } from '../types';
import { useConversation } from './useConversations';

/**
 * Drives the chat screen: local message list, sending, and loading a past
 * conversation from the store. Uses the persisted farm selection for context
 * and the current UI language for the reply.
 */
export function useChat() {
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const setActive = useChatStore((s) => s.setActive);
  const { selected } = useSelectedFarm();
  const { language } = useLanguage();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const sendingRef = useRef(false);
  const activeIdRef = useRef(activeConversationId);
  activeIdRef.current = activeConversationId;

  const detail = useConversation(activeConversationId);

  // Tracks which conversation's `messages` state is already authoritative
  // locally, so the background conversation-detail fetch below only ever
  // *hydrates* (loading a past conversation from history) and never
  // *clobbers* (overwriting optimistic messages we already know about).
  //
  // Bug this fixes: sending the first message of a brand-new conversation
  // calls setActive() once the reply arrives, which flips this query from
  // disabled to enabled. That fetch is in flight for a moment -- if the
  // user sends a second message before it resolves, the fetch would land
  // with a conversation snapshot that predates the second message and
  // overwrite local state, silently deleting the user's just-sent question
  // bubble while its reply (appended after, from `prev`) still showed up.
  const hydratedConversationIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!activeConversationId) {
      hydratedConversationIdRef.current = null;
      setMessages([]);
    } else if (detail.data && hydratedConversationIdRef.current !== activeConversationId) {
      setMessages(detail.data.messages);
      hydratedConversationIdRef.current = activeConversationId;
    } else if (hydratedConversationIdRef.current !== activeConversationId) {
      setMessages([]);
    }
  }, [activeConversationId, detail.data]);

  const send = useCallback(
    async (raw: string, retryMessageId?: string) => {
      const text = raw.trim();
      if (!text || sendingRef.current || (activeConversationId && (detail.isLoading || detail.isError))) return;
      sendingRef.current = true;

      const userMessage: ChatMessage = {
        id: `local-${uuid()}`,
        sender: 'user',
        text,
        language,
        createdAt: new Date().toISOString(),
      };
      // Once a farmer sends into an existing conversation, the local thread is
      // authoritative. A late history hydration must never replace this
      // optimistic question while the assistant reply is in flight.
      if (activeConversationId) {
        hydratedConversationIdRef.current = activeConversationId;
      }
      if (retryMessageId) {
        setMessages((prev) => prev.map((item) => (
          item.id === retryMessageId ? { ...item, sendFailed: false } : item
        )));
      } else {
        setMessages((prev) => [...prev, userMessage]);
      }
      setIsSending(true);

      try {
        const result = await getAIProvider().chat({
          message: text,
          conversationId: activeConversationId ?? undefined,
          farmId: selected?.id,
          language,
        });
        void queryClient.invalidateQueries({ queryKey: aiKeys.history });
        if (activeIdRef.current !== activeConversationId) return;
        setMessages((prev) => [
          ...prev,
          { ...result.reply, text: useAgrowAIGreeting(result.reply.text) },
        ]);
        if (!activeConversationId) {
          // Local state already has this conversation's full (and only)
          // messages -- mark it hydrated up front so the detail fetch that
          // setActive() is about to enable can't race a later optimistic
          // message and wipe it out (see the ref's comment above).
          hydratedConversationIdRef.current = result.conversationId;
          setActive(result.conversationId);
        }
        void queryClient.invalidateQueries({ queryKey: aiKeys.history });
      } catch (error) {
        if (activeIdRef.current !== activeConversationId) return;
        const errorMessageKey =
          error instanceof ApiError && error.errorCode === 'ai_daily_quota_exceeded'
            ? 'ai.quotaExceeded'
            : error instanceof ApiError && error.status === 0
              ? 'ai.networkError'
              : 'ai.errorReply';
        setMessages((prev) => prev.map((item) => (
          item.id === (retryMessageId ?? userMessage.id)
            ? { ...item, sendFailed: true }
            : item
        )));
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${uuid()}`,
            sender: 'assistant',
            text: '',
            language,
            createdAt: new Date().toISOString(),
            error: true,
            errorMessageKey,
          },
        ]);
      } finally {
        sendingRef.current = false;
        setIsSending(false);
      }
    },
    [activeConversationId, detail.isLoading, detail.isError, language, selected?.id, setActive],
  );

  const newChat = useCallback(() => {
    if (sendingRef.current) return;
    setActive(null);
    setMessages([]);
  }, [setActive]);

  const retry = useCallback((message: ChatMessage) => {
    if (message.sendFailed) void send(message.text, message.id);
  }, [send]);

  return {
    messages,
    isSending,
    send,
    retry,
    newChat,
    loadingHistory: Boolean(activeConversationId) && detail.isLoading,
    historyError: Boolean(activeConversationId) && detail.isError,
    retryHistory: () => { if (activeConversationId && !sendingRef.current) void detail.refetch(); },
  };
}
