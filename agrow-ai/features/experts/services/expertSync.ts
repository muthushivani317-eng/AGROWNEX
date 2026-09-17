import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';

import { CONSULTATION_OUTBOX_KEY } from '../constants';
import type { AttachmentInput, ConsultationStatus, ReplyInput } from '../types';
import { ExpertError, type ExpertProvider } from './expertProvider';

/**
 * Offline sync for the API provider path (docs: OFFLINE → retry, background sync).
 * Reply / attachment / status actions that fail while offline are queued here and
 * replayed on reconnect. The local provider is inherently offline and skips this.
 */
export type ConsultationOp = 'reply' | 'attachment' | 'status';

export interface ConsultationOutboxEntry {
  entryId: string;
  op: ConsultationOp;
  consultationId: string;
  reply?: ReplyInput;
  attachment?: AttachmentInput;
  status?: ConsultationStatus;
  note?: string;
}

function readOutbox(): ConsultationOutboxEntry[] {
  return appStorage.getJSON<ConsultationOutboxEntry[]>(CONSULTATION_OUTBOX_KEY) ?? [];
}

function writeOutbox(entries: ConsultationOutboxEntry[]): void {
  appStorage.setJSON(CONSULTATION_OUTBOX_KEY, entries);
}

export const consultationOutbox = {
  all: readOutbox,
  count: () => readOutbox().length,
  enqueue(entry: Omit<ConsultationOutboxEntry, 'entryId'>): void {
    writeOutbox([...readOutbox(), { ...entry, entryId: uuid() }]);
  },
  remove(entryId: string): void {
    writeOutbox(readOutbox().filter((e) => e.entryId !== entryId));
  },
  clear(): void {
    appStorage.remove(CONSULTATION_OUTBOX_KEY);
  },
};

/** True when a failure is due to connectivity (so it should be queued/retried). */
export function isOfflineError(error: unknown): boolean {
  if (error instanceof ApiError) return error.isNetwork;
  if (error instanceof ExpertError) return error.code === 'network';
  return false;
}

export interface SyncResult {
  synced: number;
  failed: number;
  remaining: number;
}

/** Replay queued consultation actions. Stops early (to retry later) if offline. */
export async function syncConsultations(provider: ExpertProvider): Promise<SyncResult> {
  let synced = 0;
  let failed = 0;

  for (const entry of readOutbox()) {
    try {
      await applyEntry(provider, entry);
      consultationOutbox.remove(entry.entryId);
      synced += 1;
    } catch (error) {
      if (isOfflineError(error)) break; // still offline — keep the queue intact
      consultationOutbox.remove(entry.entryId); // drop a poison entry
      failed += 1;
    }
  }

  return { synced, failed, remaining: consultationOutbox.count() };
}

async function applyEntry(
  provider: ExpertProvider,
  entry: ConsultationOutboxEntry,
): Promise<void> {
  if (entry.op === 'reply' && entry.reply) {
    await provider.reply(entry.consultationId, entry.reply);
    return;
  }
  if (entry.op === 'attachment' && entry.attachment) {
    await provider.addAttachment(entry.consultationId, entry.attachment);
    return;
  }
  if (entry.op === 'status' && entry.status) {
    await provider.updateStatus(entry.consultationId, entry.status, entry.note);
  }
}
