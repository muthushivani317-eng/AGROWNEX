import { appStorage } from "@/lib/storage";
import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";
import { ApiError } from "@/types";
import { useAuthStore } from "@/features/auth/store/authStore";

import type { ActionVerification, ApiActionVerification } from "./types";

export interface ActionResponseInput {
  actionId: string;
  event: "done" | "not_done" | "defer" | "skip" | "unable";
  expectedVersion: number;
  note?: string;
  idempotencyKey: string;
}

const CACHE = "agrowai.action-verification.cache";
const OUTBOX = "agrowai.action-verification.outbox";
const CONFLICTS = "agrowai.action-verification.conflicts";

function userKey(base: string): string {
  const userId = useAuthStore.getState().user?.id;
  if (!userId) throw new Error("ACTION_VERIFICATION_USER_REQUIRED");
  return `${base}.${userId}`;
}

export interface ActionConflict {
  input: ActionResponseInput;
  detectedAt: string;
}

export function mapAction(row: ApiActionVerification): ActionVerification {
  return {
    id: row.id,
    farmId: row.farm_id,
    cropCycleId: row.crop_cycle_id,
    sourceFeature: row.source_feature,
    sourceRecordId: row.source_record_id,
    actionCode: row.action_code,
    suggestionTime: row.suggestion_time,
    status: row.status,
    version: row.version,
    expiresAt: row.expires_at,
    pendingSync: row.pending_sync,
    updatedAt: row.updated_at,
  };
}

function cache(rows: ActionVerification[]) {
  appStorage.setJSON(userKey(CACHE), rows);
  return rows;
}

export async function listActions(
  pending = false,
): Promise<ActionVerification[]> {
  try {
    const rows = await api.get<ApiActionVerification[]>(
      endpoints.actionVerification.actions,
      {
        params: { pending },
      },
    );
    return cache(rows.map(mapAction));
  } catch (error) {
    if (error instanceof ApiError && error.isNetwork) {
      const saved = appStorage.getJSON<ActionVerification[]>(userKey(CACHE));
      if (saved) return saved.map((row) => ({ ...row }));
    }
    throw error;
  }
}

export async function getAction(id: string): Promise<ActionVerification> {
  return mapAction(
    await api.get<ApiActionVerification>(
      endpoints.actionVerification.detail(id),
    ),
  );
}

export interface ActionHistoryEntry {
  id: string;
  newStatus: string;
  note: string | null;
  evidenceAttached: boolean;
  createdAt: string;
}

export async function getActionHistory(
  id: string,
): Promise<ActionHistoryEntry[]> {
  const rows = await api.get<
    Array<{
      id: string;
      new_status: string;
      note: string | null;
      evidence_hash: string | null;
      created_at: string;
    }>
  >(endpoints.actionVerification.history(id));
  return rows.map((row) => ({
    id: row.id,
    newStatus: row.new_status,
    note: row.note,
    evidenceAttached: Boolean(row.evidence_hash),
    createdAt: row.created_at,
  }));
}

export async function respondToAction(
  input: ActionResponseInput,
): Promise<ActionVerification> {
  try {
    const row = await api.post<ApiActionVerification>(
      endpoints.actionVerification.respond(input.actionId),
      {
        event: input.event,
        expected_version: input.expectedVersion,
        note: input.note ?? null,
        request_id: input.idempotencyKey,
        idempotency_key: input.idempotencyKey,
        retention_consent: false,
      },
    );
    return mapAction(row);
  } catch (error) {
    if (error instanceof ApiError && error.isNetwork) {
      const outboxKey = userKey(OUTBOX);
      const queued = appStorage.getJSON<ActionResponseInput[]>(outboxKey) ?? [];
      if (!queued.some((row) => row.idempotencyKey === input.idempotencyKey)) {
        appStorage.setJSON(outboxKey, [...queued, input]);
      }
      const cached =
        appStorage.getJSON<ActionVerification[]>(userKey(CACHE)) ?? [];
      const current = cached.find((row) => row.id === input.actionId);
      if (!current) throw error;
      const status =
        input.event === "done"
          ? "farmer_reported_done"
          : input.event === "not_done"
            ? "farmer_reported_not_done"
            : input.event === "skip"
              ? "skipped"
              : input.event === "unable"
                ? "unable_to_complete"
                : "deferred";
      const pending = {
        ...current,
        status,
        pendingSync: true,
      } as ActionVerification;
      cache(cached.map((row) => (row.id === input.actionId ? pending : row)));
      return pending;
    }
    throw error;
  }
}

export async function syncActionOutbox(): Promise<number> {
  const outboxKey = userKey(OUTBOX);
  const conflictKey = userKey(CONFLICTS);
  const queued = appStorage.getJSON<ActionResponseInput[]>(outboxKey) ?? [];
  let synced = 0;
  const remaining: ActionResponseInput[] = [];
  for (const input of queued) {
    try {
      const result = await respondToAction(input);
      if (result.pendingSync) remaining.push(input);
      else synced += 1;
    } catch (error) {
      remaining.push(input);
      if (
        error instanceof ApiError &&
        error.status === 409 &&
        error.errorCode === "ACTION_VERSION_CONFLICT"
      ) {
        const conflicts =
          appStorage.getJSON<ActionConflict[]>(conflictKey) ?? [];
        if (!conflicts.some((item) => item.input.actionId === input.actionId)) {
          appStorage.setJSON(conflictKey, [
            ...conflicts,
            { input, detectedAt: new Date().toISOString() },
          ]);
        }
      }
    }
  }
  const added = (appStorage.getJSON<ActionResponseInput[]>(outboxKey) ?? [])
    .filter((item) => !queued.some((old) => old.idempotencyKey === item.idempotencyKey));
  appStorage.setJSON(outboxKey, [...remaining, ...added]);
  return synced;
}

export function getActionConflicts(): ActionConflict[] {
  return appStorage.getJSON<ActionConflict[]>(userKey(CONFLICTS)) ?? [];
}

export async function resolveActionConflict(
  actionId: string,
  resolution: "keep_server" | "apply_mine",
): Promise<ActionVerification> {
  const conflicts = getActionConflicts();
  const conflict = conflicts.find((item) => item.input.actionId === actionId);
  if (!conflict) throw new Error("ACTION_CONFLICT_NOT_FOUND");
  const latest = await getAction(actionId);
  let result = latest;
  if (resolution === "apply_mine") {
    result = await respondToAction({
      ...conflict.input,
      expectedVersion: latest.version,
      idempotencyKey: `${conflict.input.idempotencyKey}-resolved`,
    });
  }
  appStorage.setJSON(
    userKey(CONFLICTS),
    conflicts.filter((item) => item.input.actionId !== actionId),
  );
  const queued =
    appStorage.getJSON<ActionResponseInput[]>(userKey(OUTBOX)) ?? [];
  appStorage.setJSON(
    userKey(OUTBOX),
    queued.filter((item) => item.idempotencyKey !== conflict.input.idempotencyKey),
  );
  return result;
}
