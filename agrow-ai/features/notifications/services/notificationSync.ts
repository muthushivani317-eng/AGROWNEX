import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { NOTIFICATION_OUTBOX_KEY } from '../constants';
import { NotificationError, type NotificationProvider } from './notificationProvider';

/**
 * Offline sync for the API provider path (docs: OFFLINE → retry, background sync).
 * Read/mark-all/dismiss actions that fail while offline are queued here and
 * replayed on reconnect. The local provider is inherently offline and skips this.
 */
export type NotificationOp = 'read' | 'readAll' | 'dismiss';

export interface NotificationOutboxEntry {
  entryId: string;
  op: NotificationOp;
  notificationId?: string;
}

function readOutbox(): NotificationOutboxEntry[] {
  return appStorage.getJSON<NotificationOutboxEntry[]>(NOTIFICATION_OUTBOX_KEY) ?? [];
}

function writeOutbox(entries: NotificationOutboxEntry[]): void {
  appStorage.setJSON(NOTIFICATION_OUTBOX_KEY, entries);
}

export const notificationOutbox = {
  all: readOutbox,
  count: () => readOutbox().length,
  enqueue(entry: Omit<NotificationOutboxEntry, 'entryId'>): void {
    writeOutbox([...readOutbox(), { ...entry, entryId: uuid() }]);
  },
  remove(entryId: string): void {
    writeOutbox(readOutbox().filter((e) => e.entryId !== entryId));
  },
  clear(): void {
    appStorage.remove(NOTIFICATION_OUTBOX_KEY);
  },
};

/** True when a failure is due to connectivity (so it should be queued/retried). */
export function isOfflineError(error: unknown): boolean {
  if (error instanceof ApiError) return error.isNetwork;
  if (error instanceof NotificationError) return error.code === 'network';
  return false;
}

export interface SyncResult {
  synced: number;
  failed: number;
  remaining: number;
}

/** Replay queued notification actions. Stops early (to retry later) if offline. */
export async function syncNotifications(
  provider: NotificationProvider,
): Promise<SyncResult> {
  let synced = 0;
  let failed = 0;

  for (const entry of readOutbox()) {
    try {
      await applyEntry(provider, entry);
      notificationOutbox.remove(entry.entryId);
      synced += 1;
    } catch (error) {
      if (isOfflineError(error)) break; // still offline — keep the queue intact
      // Server rejection (e.g. already dismissed): drop to avoid a poison loop.
      notificationOutbox.remove(entry.entryId);
      failed += 1;
    }
  }

  return { synced, failed, remaining: notificationOutbox.count() };
}

async function applyEntry(
  provider: NotificationProvider,
  entry: NotificationOutboxEntry,
): Promise<void> {
  if (entry.op === 'read' && entry.notificationId) {
    await provider.markRead(entry.notificationId);
    return;
  }
  if (entry.op === 'readAll') {
    await provider.markAllRead();
    return;
  }
  if (entry.op === 'dismiss' && entry.notificationId) {
    await provider.dismiss(entry.notificationId);
  }
}
