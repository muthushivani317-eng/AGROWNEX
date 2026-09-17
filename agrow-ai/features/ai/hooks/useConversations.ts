import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { aiKeys } from '../constants';
import { getAIProvider } from '../services/aiProvider';

/** The farmer's conversation history (most recent first). */
export function useConversations() {
  return useQuery({
    queryKey: aiKeys.history,
    queryFn: () => getAIProvider().listConversations(),
  });
}

/** A single conversation with its full message thread. */
export function useConversation(id: string | null) {
  return useQuery({
    queryKey: aiKeys.conversation(id ?? 'none'),
    enabled: Boolean(id),
    queryFn: () => getAIProvider().getConversation(id as string),
  });
}

export function useDeleteConversation() {
  return useMutation({
    mutationFn: (id: string) => getAIProvider().deleteConversation(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: aiKeys.all });
    },
  });
}
