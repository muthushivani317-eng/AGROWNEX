import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { consultationKeys, DEFAULT_PAGE_SIZE } from '../constants';
import { getExpertProvider } from '../services/expertProvider';
import { consultationListKey } from '../services/expertStorage';
import { consultationOutbox, isOfflineError } from '../services/expertSync';
import type {
  AttachmentInput,
  ConsultationInput,
  ConsultationListParams,
  ConsultationStatus,
  ReplyInput,
} from '../types';

const LIST_STALE = 60 * 1000;

export function useConsultationList(params: ConsultationListParams = {}, enabled = true) {
  return useQuery({
    queryKey: consultationKeys.list(
      consultationListKey('all', params as Record<string, unknown>),
    ),
    enabled,
    queryFn: () =>
      getExpertProvider().listConsultations({ pageSize: DEFAULT_PAGE_SIZE, ...params }),
    staleTime: LIST_STALE,
  });
}

export function usePendingConsultations(enabled = true) {
  return useQuery({
    queryKey: consultationKeys.pending,
    enabled,
    queryFn: () => getExpertProvider().pending(),
    staleTime: LIST_STALE,
  });
}

export function useConsultationHistory(enabled = true) {
  return useQuery({
    queryKey: consultationKeys.history,
    enabled,
    queryFn: () => getExpertProvider().history(),
    staleTime: LIST_STALE,
  });
}

export function useConsultationDetail(id: string | undefined) {
  return useQuery({
    queryKey: consultationKeys.detail(id ?? ''),
    enabled: Boolean(id),
    queryFn: () => getExpertProvider().getConsultation(id as string),
  });
}

function invalidateLists(): void {
  void queryClient.invalidateQueries({ queryKey: consultationKeys.all });
}

function invalidateDetail(id: string): void {
  invalidateLists();
  void queryClient.invalidateQueries({ queryKey: consultationKeys.detail(id) });
}

export function useCreateConsultation() {
  return useMutation({
    mutationFn: (input: ConsultationInput) =>
      getExpertProvider().createConsultation(input),
    onSuccess: invalidateLists,
  });
}

export interface MutationResult {
  offline: boolean;
}

export function useReplyConsultation(id: string) {
  return useMutation<MutationResult, unknown, ReplyInput>({
    mutationFn: async (input) => {
      try {
        await getExpertProvider().reply(id, input);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          consultationOutbox.enqueue({ op: 'reply', consultationId: id, reply: input });
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: () => invalidateDetail(id),
  });
}

export function useAddConsultationAttachment(id: string) {
  return useMutation<MutationResult, unknown, AttachmentInput>({
    mutationFn: async (attachment) => {
      try {
        await getExpertProvider().addAttachment(id, attachment);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          consultationOutbox.enqueue({
            op: 'attachment',
            consultationId: id,
            attachment,
          });
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: () => invalidateDetail(id),
  });
}

export function useUpdateConsultationStatus(id: string) {
  return useMutation<MutationResult, unknown, { status: ConsultationStatus; note?: string }>(
    {
      mutationFn: async ({ status, note }) => {
        try {
          await getExpertProvider().updateStatus(id, status, note);
          return { offline: false };
        } catch (error) {
          if (isOfflineError(error)) {
            consultationOutbox.enqueue({
              op: 'status',
              consultationId: id,
              status,
              note,
            });
            return { offline: true };
          }
          throw error;
        }
      },
      onSuccess: () => invalidateDetail(id),
    },
  );
}
