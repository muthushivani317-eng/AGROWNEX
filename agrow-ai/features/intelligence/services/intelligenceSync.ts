import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { INTEL_OUTBOX_KEY } from '../constants';
import { IntelligenceError, type IntelligenceProvider } from './intelligenceProvider';

/**
 * Offline sync for the API provider path (docs: OFFLINE → retry, background sync). A
 * refresh requested while offline is queued here and replayed on reconnect. The local
 * provider is inherently offline and skips this.
 */
export interface IntelligenceOutboxEntry {
  entryId: string;
  farmId: string;
}

function readOutbox(): IntelligenceOutboxEntry[] {
  return appStorage.getJSON<IntelligenceOutboxEntry[]>(INTEL_OUTBOX_KEY) ?? [];
}

function writeOutbox(entries: IntelligenceOutboxEntry[]): void {
  appStorage.setJSON(INTEL_OUTBOX_KEY, entries);
}

export const intelligenceOutbox = {
  all: readOutbox,
  count: () => readOutbox().length,
  enqueue(farmId: string): void {
    // Collapse duplicate refresh requests for the same farm.
    const existing = readOutbox().filter((e) => e.farmId !== farmId);
    writeOutbox([...existing, { entryId: uuid(), farmId }]);
  },
  remove(entryId: string): void {
    writeOutbox(readOutbox().filter((e) => e.entryId !== entryId));
  },
  clear(): void {
    appStorage.remove(INTEL_OUTBOX_KEY);
  },
};

/** True when a failure is due to connectivity (so it should be queued/retried). */
export function isOfflineError(error: unknown): boolean {
  if (error instanceof ApiError) return error.isNetwork;
  if (error instanceof IntelligenceError) return error.code === 'network';
  return false;
}

export interface SyncResult {
  synced: number;
  failed: number;
  remaining: number;
}

/** Replay queued intelligence refreshes. Stops early (to retry later) if offline. */
export async function syncIntelligence(provider: IntelligenceProvider): Promise<SyncResult> {
  let synced = 0;
  let failed = 0;

  for (const entry of readOutbox()) {
    try {
      await provider.refresh(entry.farmId);
      intelligenceOutbox.remove(entry.entryId);
      synced += 1;
    } catch (error) {
      if (isOfflineError(error)) break; // still offline — keep the queue intact
      intelligenceOutbox.remove(entry.entryId); // drop a poison entry
      failed += 1;
    }
  }

  return { synced, failed, remaining: intelligenceOutbox.count() };
}
