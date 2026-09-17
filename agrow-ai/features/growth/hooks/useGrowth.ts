import { useMutation, useQuery } from "@tanstack/react-query";

import { queryClient } from "@/lib/queryClient";

import { growthKeys } from "../constants";
import { getGrowthProvider } from "../services/growthProvider";
import type { UploadGrowthInput } from "../types";
import {
  getStageHistory,
  getStageState,
  submitStageTransition,
} from "../services/apiGrowthProvider";
import type { StageTransitionInput } from "../types";

export function useStageState(
  farmId?: string | null,
  cropCycleId?: string | null,
) {
  return useQuery({
    queryKey: ["growth", "stage", farmId, cropCycleId],
    queryFn: () => getStageState(farmId!, cropCycleId!),
    enabled: Boolean(farmId && cropCycleId),
  });
}

export function useStageHistory(stateId?: string | null) {
  return useQuery({
    queryKey: ["growth", "stage", "history", stateId],
    queryFn: () => getStageHistory(stateId!),
    enabled: Boolean(stateId),
  });
}

export function useStageTransition() {
  return useMutation({
    mutationFn: (input: StageTransitionInput) => submitStageTransition(input),
    onSuccess: (state) => {
      queryClient.setQueryData(
        ["growth", "stage", state.farmId, state.cropCycleId],
        state,
      );
      void queryClient.invalidateQueries({
        queryKey: ["growth", "stage", "history", state.id],
      });
    },
  });
}

/** All uploaded photos (most recent first), optionally for one session. */
export function useGrowthHistory(
  sessionId?: string | null,
  farmId?: string | null,
  enabled = true,
) {
  return useQuery({
    queryKey: growthKeys.history(sessionId ?? null, farmId ?? null),
    queryFn: () => getGrowthProvider().history(sessionId, farmId),
    enabled,
  });
}

/** Week 1 → Week N timeline for a session (defaults to the latest). */
export function useGrowthTimeline(
  sessionId?: string | null,
  farmId?: string | null,
  enabled = true,
) {
  return useQuery({
    queryKey: growthKeys.timeline(sessionId ?? null, farmId ?? null),
    queryFn: () => getGrowthProvider().timeline(sessionId, farmId),
    enabled,
    retry: false,
  });
}

/** The most recent uploaded photo + analysis (null if none yet). */
export function useGrowthLatest() {
  return useQuery({
    queryKey: growthKeys.latest,
    queryFn: () => getGrowthProvider().latest(),
  });
}

/** Full session detail (metadata, all photos with analysis, timeline). */
export function useGrowthSession(id: string | null) {
  return useQuery({
    queryKey: growthKeys.session(id ?? "none"),
    enabled: Boolean(id),
    queryFn: () => getGrowthProvider().session(id as string),
  });
}

/** Upload a validated crop photo → growth analysis + timeline entry. */
export function useUploadGrowth() {
  return useMutation({
    mutationFn: (input: UploadGrowthInput) => getGrowthProvider().upload(input),
    retry: false,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: growthKeys.all });
    },
  });
}

export function useDeleteGrowthImage() {
  return useMutation({
    mutationFn: (id: string) => getGrowthProvider().deleteImage(id),
    retry: false,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: growthKeys.all });
    },
  });
}
