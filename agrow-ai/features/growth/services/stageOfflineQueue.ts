import { appStorage } from "@/lib/storage";

import type { StageTransitionInput } from "../types";

const KEY = "growth.stage.pending.v1";

export function pendingStageTransitions(): StageTransitionInput[] {
  return appStorage.getJSON<StageTransitionInput[]>(KEY) ?? [];
}

export function queueStageTransition(input: StageTransitionInput): void {
  const existing = pendingStageTransitions();
  if (existing.some((item) => item.idempotencyKey === input.idempotencyKey))
    return;
  appStorage.setJSON(KEY, [...existing, input]);
}

export function removePendingStageTransition(idempotencyKey: string): void {
  appStorage.setJSON(
    KEY,
    pendingStageTransitions().filter(
      (item) => item.idempotencyKey !== idempotencyKey,
    ),
  );
}

export async function syncPendingStageTransitions(
  send: (input: StageTransitionInput) => Promise<unknown>,
): Promise<{ synced: number; remaining: number }> {
  let synced = 0;
  for (const item of pendingStageTransitions()) {
    try {
      await send(item);
      removePendingStageTransition(item.idempotencyKey);
      synced += 1;
    } catch {
      break;
    }
  }
  return { synced, remaining: pendingStageTransitions().length };
}
