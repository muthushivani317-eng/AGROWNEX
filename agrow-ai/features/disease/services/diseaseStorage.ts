import { appStorage } from "@/lib/storage";
import { useAuthStore } from "@/features/auth/store/authStore";

import { DISEASE_STORE_KEY } from "../constants";
import type { DiseaseReport } from "../types";

/** Local disease-report mirror in MMKV (local provider + offline history). */
interface DiseaseCacheEnvelope {
  ownerUserId: string;
  farmId: string | null;
  reports: DiseaseReport[];
}

const UNASSIGNED_FARM = "unassigned";

function currentUserId(): string | null {
  return useAuthStore.getState().user?.id ?? null;
}

function userPrefix(userId: string): string {
  return `${DISEASE_STORE_KEY}:${encodeURIComponent(userId)}`;
}

function farmScope(farmId: string | null): string {
  return encodeURIComponent(farmId ?? UNASSIGNED_FARM);
}

function farmKey(userId: string, farmId: string | null): string {
  return `${userPrefix(userId)}:${farmScope(farmId)}`;
}

function farmIndexKey(userId: string): string {
  return `${userPrefix(userId)}:farm-index`;
}

function legacyUserKey(userId: string): string {
  return `${DISEASE_STORE_KEY}.${userId}`;
}

function readFarmIndex(userId: string): Array<string | null> {
  return appStorage.getJSON<Array<string | null>>(farmIndexKey(userId)) ?? [];
}

function writeFarmIndex(userId: string, farmIds: Array<string | null>): void {
  appStorage.setJSON(farmIndexKey(userId), [...new Set(farmIds)]);
}

function readFarm(userId: string, farmId: string | null): DiseaseReport[] {
  const envelope = appStorage.getJSON<DiseaseCacheEnvelope>(
    farmKey(userId, farmId),
  );
  if (
    !envelope ||
    envelope.ownerUserId !== userId ||
    envelope.farmId !== farmId
  )
    return [];
  return envelope.reports.filter((report) => report.farmId === farmId);
}

function writeFarm(
  userId: string,
  farmId: string | null,
  reports: DiseaseReport[],
): void {
  appStorage.setJSON(farmKey(userId, farmId), {
    ownerUserId: userId,
    farmId,
    reports: reports.filter((report) => report.farmId === farmId),
  } satisfies DiseaseCacheEnvelope);
  writeFarmIndex(userId, [...readFarmIndex(userId), farmId]);
}

function migrateLegacyCache(userId: string): void {
  const scopedLegacy = appStorage.getJSON<DiseaseReport[]>(
    legacyUserKey(userId),
  );
  if (scopedLegacy) {
    for (const report of scopedLegacy) {
      const reports = readFarm(userId, report.farmId);
      writeFarm(userId, report.farmId, [...reports, report]);
    }
    appStorage.remove(legacyUserKey(userId));
  }

  // The original flat cache has no ownership metadata, so assigning it to the
  // current account could expose another user's diagnoses on a shared device.
  // It is unrecoverable safely and must remain unreadable.
  if (appStorage.getString(DISEASE_STORE_KEY) !== null) {
    appStorage.remove(DISEASE_STORE_KEY);
  }
}

function readAll(): DiseaseReport[] {
  const userId = currentUserId();
  if (!userId) return [];
  migrateLegacyCache(userId);
  return readFarmIndex(userId).flatMap((farmId) => readFarm(userId, farmId));
}

export const diseaseStorage = {
  all(): DiseaseReport[] {
    return readAll();
  },
  get(id: string): DiseaseReport | null {
    return readAll().find((r) => r.id === id) ?? null;
  },
  upsert(report: DiseaseReport): void {
    const userId = currentUserId();
    if (!userId) return;
    migrateLegacyCache(userId);
    const list = readFarm(userId, report.farmId);
    const index = list.findIndex((r) => r.id === report.id);
    if (index >= 0) list[index] = report;
    else list.unshift(report);
    writeFarm(userId, report.farmId, list);
  },
  remove(id: string): void {
    const userId = currentUserId();
    if (!userId) return;
    migrateLegacyCache(userId);
    for (const farmId of readFarmIndex(userId)) {
      const reports = readFarm(userId, farmId);
      if (reports.some((report) => report.id === id)) {
        writeFarm(
          userId,
          farmId,
          reports.filter((report) => report.id !== id),
        );
      }
    }
  },
  clear(): void {
    const userId = currentUserId();
    if (!userId) return;
    for (const farmId of readFarmIndex(userId)) {
      appStorage.remove(farmKey(userId, farmId));
    }
    appStorage.remove(farmIndexKey(userId));
    appStorage.remove(legacyUserKey(userId));
  },
};
