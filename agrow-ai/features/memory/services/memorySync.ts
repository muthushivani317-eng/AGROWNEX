import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { MEMORY_OUTBOX_KEY } from '../constants';
import { MemoryError, type MemoryProvider } from './memoryProvider';

/**
 * Offline sync for the API provider path (docs: OFFLINE → retry, background sync). A
 * rebuild requested while offline is queued here and replayed on reconnect. The local
 * provider is inherently offline and skips this.
 */
export interface MemoryOutboxEntry {
  entryId: string;
  farmId: string;
}

function readOutbox(): MemoryOutboxEntry[] {
  return appStorage.getJSON<MemoryOutboxEntry[]>(MEMORY_OUTBOX_KEY) ?? [];
}

function writeOutbox(entries: MemoryOutboxEntry[]): void {
  appStorage.setJSON(MEMORY_OUTBOX_KEY, entries);
}

export const memoryOutbox = {
  all: readOutbox,
  count: () => readOutbox().length,
  enqueue(farmId: string): void {
    // Collapse duplicate rebuild requests for the same farm.
    const existing = readOutbox().filter((e) => e.farmId !== farmId);
    writeOutbox([...existing, { entryId: uuid(), farmId }]);
  },
  remove(entryId: string): void {
    writeOutbox(readOutbox().filter((e) => e.entryId !== entryId));
  },
  clear(): void {
    appStorage.remove(MEMORY_OUTBOX_KEY);
  },
};

/** True when a failure is due to connectivity (so it should be queued/retried). */
export function isOfflineError(error: unknown): boolean {
  if (error instanceof ApiError) return error.isNetwork;
  if (error instanceof MemoryError) return error.code === 'network';
  return false;
}

export interface SyncResult {
  synced: number;
  failed: number;
  remaining: number;
}

/** Replay queued memory rebuilds. Stops early (to retry later) if still offline. */
export async function syncMemory(provider: MemoryProvider): Promise<SyncResult> {
  let synced = 0;
  let failed = 0;

  for (const entry of readOutbox()) {
    try {
      await provider.rebuild(entry.farmId);
      memoryOutbox.remove(entry.entryId);
      synced += 1;
    } catch (error) {
      if (isOfflineError(error)) break; // still offline — keep the queue intact
      memoryOutbox.remove(entry.entryId); // drop a poison entry
      failed += 1;
    }
  }

  return { synced, failed, remaining: memoryOutbox.count() };
}
