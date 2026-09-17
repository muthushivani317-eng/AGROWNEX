import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { SOIL_OUTBOX_KEY } from '../constants';
import type { SoilReportInput } from '../types';
import { SoilError, type SoilProvider } from './soilProvider';

/**
 * Offline sync for the API provider path (docs: OFFLINE → retry, background sync).
 * A soil report submitted while offline is queued here and replayed on reconnect.
 * The local provider is inherently offline and skips this.
 */
export interface SoilOutboxEntry {
  entryId: string;
  input: SoilReportInput;
}

function readOutbox(): SoilOutboxEntry[] {
  return appStorage.getJSON<SoilOutboxEntry[]>(SOIL_OUTBOX_KEY) ?? [];
}

function writeOutbox(entries: SoilOutboxEntry[]): void {
  appStorage.setJSON(SOIL_OUTBOX_KEY, entries);
}

export const soilOutbox = {
  all: readOutbox,
  count: () => readOutbox().length,
  enqueue(input: SoilReportInput): void {
    writeOutbox([...readOutbox(), { entryId: uuid(), input }]);
  },
  remove(entryId: string): void {
    writeOutbox(readOutbox().filter((e) => e.entryId !== entryId));
  },
  clear(): void {
    appStorage.remove(SOIL_OUTBOX_KEY);
  },
};

/** True when a failure is due to connectivity (so it should be queued/retried). */
export function isOfflineError(error: unknown): boolean {
  if (error instanceof ApiError) return error.isNetwork;
  if (error instanceof SoilError) return error.code === 'network';
  return false;
}

export interface SyncResult {
  synced: number;
  failed: number;
  remaining: number;
}

/** Replay queued soil reports. Stops early (to retry later) if still offline. */
export async function syncSoil(provider: SoilProvider): Promise<SyncResult> {
  let synced = 0;
  let failed = 0;

  for (const entry of readOutbox()) {
    try {
      await provider.submitReport(entry.input);
      soilOutbox.remove(entry.entryId);
      synced += 1;
    } catch (error) {
      if (isOfflineError(error)) break; // still offline — keep the queue intact
      soilOutbox.remove(entry.entryId); // drop a poison entry
      failed += 1;
    }
  }

  return { synced, failed, remaining: soilOutbox.count() };
}
