import { useInfiniteQuery, useMutation, useQuery } from "@tanstack/react-query";

import { queryClient } from "@/lib/queryClient";

import { dailyTaskKeys } from "../constants";
import {
  fetchEvidencePack,
  fetchTask,
  fetchTaskHistory,
  fetchTodayTasks,
  respondToTask,
  shareEvidencePack,
  snoozeTask,
  triggerEvidencePack,
  uploadTaskPhoto,
  uploadTaskVoiceNote,
} from "../services/dailyTaskApi";
import type {
  EvidencePackShareTarget,
  TaskRespondRequest,
  TriggerEvidencePackInput,
} from "../types";

// Tasks are (re)generated server-side once a day (see backend
// app/worker.py cron at 04:00) -- a short client staleTime just avoids a
// redundant refetch on every screen focus within the same session.
const TODAY_STALE_MS = 5 * 60 * 1000;

export function useTodayTasks() {
  return useQuery({
    queryKey: dailyTaskKeys.today(),
    queryFn: fetchTodayTasks,
    staleTime: TODAY_STALE_MS,
  });
}

export function useTaskHistory() {
  return useInfiniteQuery({
    queryKey: dailyTaskKeys.history(),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => fetchTaskHistory(pageParam),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });
}

export function useTask(taskId: string | undefined) {
  return useQuery({
    queryKey: dailyTaskKeys.detail(taskId ?? ""),
    queryFn: () => fetchTask(taskId as string),
    enabled: Boolean(taskId),
  });
}

function invalidateTasks(): void {
  void queryClient.invalidateQueries({ queryKey: dailyTaskKeys.all });
}

export function useRespondToTask(taskId: string) {
  return useMutation({
    mutationFn: (body: TaskRespondRequest) => respondToTask(taskId, body),
    onSuccess: invalidateTasks,
  });
}

export function useSnoozeTask(taskId: string) {
  return useMutation({
    mutationFn: (snoozeUntil: "later_today" | "tomorrow_morning") =>
      snoozeTask(taskId, snoozeUntil),
    onSuccess: invalidateTasks,
  });
}

export function useUploadTaskPhoto(taskId: string) {
  return useMutation({
    mutationFn: (fileUri: string) => uploadTaskPhoto(taskId, fileUri),
  });
}

export function useUploadTaskVoiceNote(taskId: string) {
  return useMutation({
    mutationFn: ({
      fileUri,
      durationSeconds,
    }: {
      fileUri: string;
      durationSeconds: number;
    }) => uploadTaskVoiceNote(taskId, fileUri, durationSeconds),
  });
}

export function useEvidencePack(packId: string | undefined) {
  return useQuery({
    queryKey: dailyTaskKeys.evidencePack(packId ?? ""),
    queryFn: () => fetchEvidencePack(packId as string),
    enabled: Boolean(packId),
  });
}

export function useTriggerEvidencePack() {
  return useMutation({
    mutationFn: (input: TriggerEvidencePackInput) => triggerEvidencePack(input),
  });
}

export function useShareEvidencePack(packId: string) {
  return useMutation({
    mutationFn: ({
      shareWith,
      fpoContactId,
    }: {
      shareWith: EvidencePackShareTarget;
      fpoContactId?: string;
    }) => shareEvidencePack(packId, shareWith, fpoContactId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: dailyTaskKeys.evidencePack(packId),
      });
    },
  });
}
