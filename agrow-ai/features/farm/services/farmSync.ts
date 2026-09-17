import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { FARM_OUTBOX_KEY } from '../constants';
import type { Farm, FarmInput } from '../types';
import { FarmError, type FarmProvider } from './farmProvider';
import { farmStorage } from './farmStorage';

/**
 * Offline sync for the API provider path (docs: OFFLINE → queue synchronization,
 * conflict handling). Mutations that fail while offline are appended to this
 * outbox and replayed on reconnect; conflicts are resolved last-write-wins by
 * `updatedAt`. The local provider is inherently offline and does not use this.
 */
export type FarmOp = 'create' | 'update' | 'delete';

export interface FarmOutboxEntry {
  entryId: string;
  op: FarmOp;
  farmId: string;
  input?: FarmInput;
}

function readOutbox(): FarmOutboxEntry[] {
  return appStorage.getJSON<FarmOutboxEntry[]>(FARM_OUTBOX_KEY) ?? [];
}

function writeOutbox(entries: FarmOutboxEntry[]): void {
  appStorage.setJSON(FARM_OUTBOX_KEY, entries);
}

export const farmOutbox = {
  all: readOutbox,
  count: () => readOutbox().length,
  enqueue(entry: Omit<FarmOutboxEntry, 'entryId'>): void {
    writeOutbox([...readOutbox(), { ...entry, entryId: uuid() }]);
  },
  remove(entryId: string): void {
    writeOutbox(readOutbox().filter((e) => e.entryId !== entryId));
  },
  clear(): void {
    appStorage.remove(FARM_OUTBOX_KEY);
  },
};

/** Last-write-wins by `updatedAt`; ties and unknown timestamps favour the server. */
export function resolveFarmConflict(local: Farm, remote: Farm): Farm {
  const localTime = Date.parse(local.updatedAt ?? '') || 0;
  const remoteTime = Date.parse(remote.updatedAt ?? '') || 0;
  if (localTime > remoteTime) return { ...local, syncStatus: 'synced' };
  return { ...remote, syncStatus: 'synced' };
}

/** True when a failure is due to connectivity (so it should be queued/retried). */
export function isOfflineError(error: unknown): boolean {
  if (error instanceof ApiError) return error.isNetwork;
  if (error instanceof FarmError) return error.code === 'network';
  return false;
}

export interface SyncResult {
  synced: number;
  failed: number;
  remaining: number;
}

/** Replay queued farm mutations. Stops early (to retry later) if still offline. */
export async function syncFarms(provider: FarmProvider): Promise<SyncResult> {
  let synced = 0;
  let failed = 0;

  for (const entry of readOutbox()) {
    try {
      await applyEntry(provider, entry);
      farmOutbox.remove(entry.entryId);
      synced += 1;
    } catch (error) {
      if (isOfflineError(error)) break; // still offline — keep the queue intact
      // Validation/other server rejection: drop the entry to avoid a poison loop.
      farmOutbox.remove(entry.entryId);
      failed += 1;
    }
  }

  return { synced, failed, remaining: farmOutbox.count() };
}

async function applyEntry(provider: FarmProvider, entry: FarmOutboxEntry): Promise<void> {
  if (entry.op === 'create' && entry.input) {
    const remote = await provider.create(entry.input);
    farmStorage.remove(entry.farmId); // drop the temp record
    farmStorage.upsert(remote);
    return;
  }
  if (entry.op === 'update' && entry.input) {
    const remote = await provider.update(entry.farmId, entry.input);
    const local = farmStorage.get(entry.farmId);
    farmStorage.upsert(local ? resolveFarmConflict(local, remote) : remote);
    return;
  }
  if (entry.op === 'delete') {
    await provider.remove(entry.farmId);
    farmStorage.remove(entry.farmId);
  }
}
