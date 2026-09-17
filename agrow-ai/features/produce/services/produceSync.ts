import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { PRODUCE_OUTBOX_KEY } from '../constants';
import type { ProduceInput } from '../types';
import { ProduceError, type ProduceProvider } from './produceProvider';
import { currentProduceUserId, discardUnscopedProduceData, produceScopedKey } from './produceUserScope';

/**
 * Offline sync for the API provider path (docs: OFFLINE → queue synchronization,
 * background sync, retry). Mutations that fail while offline are appended to this
 * outbox and replayed on reconnect. The local provider is inherently offline and
 * does not use this.
 */
export type ProduceOp = 'create' | 'update' | 'delete';

export interface ProduceOutboxEntry {
  entryId: string;
  op: ProduceOp;
  offerId: string;
  input?: ProduceInput;
}

function readOutbox(): ProduceOutboxEntry[] {
  discardUnscopedProduceData(PRODUCE_OUTBOX_KEY);
  const userId = currentProduceUserId();
  return userId ? appStorage.getJSON<ProduceOutboxEntry[]>(produceScopedKey(PRODUCE_OUTBOX_KEY, userId)) ?? [] : [];
}

function writeOutbox(entries: ProduceOutboxEntry[]): void {
  const userId = currentProduceUserId();
  if (userId) appStorage.setJSON(produceScopedKey(PRODUCE_OUTBOX_KEY, userId), entries);
}

export const produceOutbox = {
  all: readOutbox,
  count: () => readOutbox().length,
  enqueue(entry: Omit<ProduceOutboxEntry, 'entryId'>): void {
    writeOutbox([...readOutbox(), { ...entry, entryId: uuid() }]);
  },
  remove(entryId: string): void {
    writeOutbox(readOutbox().filter((e) => e.entryId !== entryId));
  },
  clear(): void {
    const userId = currentProduceUserId();
    if (userId) appStorage.remove(produceScopedKey(PRODUCE_OUTBOX_KEY, userId));
  },
};

/** True when a failure is due to connectivity (so it should be queued/retried). */
export function isOfflineError(error: unknown): boolean {
  if (error instanceof ApiError) return error.isNetwork;
  if (error instanceof ProduceError) return error.code === 'network';
  return false;
}

export interface SyncResult {
  synced: number;
  failed: number;
  remaining: number;
}

/** Replay queued produce mutations. Stops early (to retry later) if still offline. */
export async function syncProduce(provider: ProduceProvider): Promise<SyncResult> {
  let synced = 0;
  let failed = 0;

  for (const entry of readOutbox()) {
    try {
      await applyEntry(provider, entry);
      produceOutbox.remove(entry.entryId);
      synced += 1;
    } catch (error) {
      if (isOfflineError(error)) break; // still offline — keep the queue intact
      // Validation/other server rejection: drop the entry to avoid a poison loop.
      produceOutbox.remove(entry.entryId);
      failed += 1;
    }
  }

  return { synced, failed, remaining: produceOutbox.count() };
}

async function applyEntry(
  provider: ProduceProvider,
  entry: ProduceOutboxEntry,
): Promise<void> {
  if (entry.op === 'create' && entry.input) {
    await provider.create(entry.input);
    return;
  }
  if (entry.op === 'update' && entry.input) {
    await provider.update(entry.offerId, entry.input);
    return;
  }
  if (entry.op === 'delete') {
    await provider.remove(entry.offerId);
  }
}
