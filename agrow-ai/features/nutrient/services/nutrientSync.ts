import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { NUT_OUTBOX_KEY } from '../constants';
import { NutrientError, type NutrientProvider } from './nutrientProvider';
import type { AnalyzeInput } from '../types';

/**
 * Offline sync for the API provider path (docs: OFFLINE → retry, background sync).
 * An analysis requested while offline is queued here and replayed on reconnect. The
 * local provider is inherently offline and skips this.
 */
export interface NutrientOutboxEntry {
  entryId: string;
  input: AnalyzeInput;
}

function readOutbox(): NutrientOutboxEntry[] {
  return appStorage.getJSON<NutrientOutboxEntry[]>(NUT_OUTBOX_KEY) ?? [];
}

function writeOutbox(entries: NutrientOutboxEntry[]): void {
  appStorage.setJSON(NUT_OUTBOX_KEY, entries);
}

export const nutrientOutbox = {
  all: readOutbox,
  count: () => readOutbox().length,
  enqueue(input: AnalyzeInput): void {
    writeOutbox([...readOutbox(), { entryId: uuid(), input }]);
  },
  remove(entryId: string): void {
    writeOutbox(readOutbox().filter((e) => e.entryId !== entryId));
  },
  clear(): void {
    appStorage.remove(NUT_OUTBOX_KEY);
  },
};

/** True when a failure is due to connectivity (so it should be queued/retried). */
export function isOfflineError(error: unknown): boolean {
  if (error instanceof ApiError) return error.isNetwork;
  if (error instanceof NutrientError) return error.code === 'network';
  return false;
}

export interface SyncResult {
  synced: number;
  failed: number;
  remaining: number;
}

/** Replay queued analyses. Stops early (to retry later) if still offline. */
export async function syncNutrient(provider: NutrientProvider): Promise<SyncResult> {
  let synced = 0;
  let failed = 0;

  for (const entry of readOutbox()) {
    try {
      await provider.analyze(entry.input);
      nutrientOutbox.remove(entry.entryId);
      synced += 1;
    } catch (error) {
      if (isOfflineError(error)) break; // still offline — keep the queue intact
      nutrientOutbox.remove(entry.entryId); // drop a poison entry
      failed += 1;
    }
  }

  return { synced, failed, remaining: nutrientOutbox.count() };
}
