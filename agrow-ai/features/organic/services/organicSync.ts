import { useAuthStore } from '@/features/auth/store/authStore';
import { appStorage } from '@/lib/storage';
import { ApiError } from '@/types';
import { uuid } from '@/utils/id';
import { ORGANIC_OUTBOX } from '../constants';
import type { OrganicFarmProfileInput, OrganicPracticeInput } from '../types';
import type { OrganicProvider } from './organicProvider';
import { organicStorage } from './organicStorage';

export type OrganicOutboxEntry =
  | { entryId: string; op: 'save_profile'; farmId: string; input: OrganicFarmProfileInput; idempotencyKey: string }
  | { entryId: string; op: 'create_practice'; farmId: string; input: OrganicPracticeInput };
const storageKey = () => { const id = useAuthStore.getState().user?.id; return id ? `${ORGANIC_OUTBOX}:${encodeURIComponent(id)}` : null; };
const read = () => { const k = storageKey(); return k ? appStorage.getJSON<OrganicOutboxEntry[]>(k) ?? [] : []; };
const write = (rows: OrganicOutboxEntry[]) => { const k = storageKey(); if (k) appStorage.setJSON(k, rows); };
export const organicOutbox = {
  all: read,
  count: () => read().length,
  enqueue(entry: { op: 'save_profile'; farmId: string; input: OrganicFarmProfileInput; idempotencyKey: string } | { op: 'create_practice'; farmId: string; input: OrganicPracticeInput }) { write([...read(), { ...entry, entryId: uuid() } as OrganicOutboxEntry]); },
  remove(entryId: string) { write(read().filter((row) => row.entryId !== entryId)); },
};
export const isOrganicOfflineError = (error: unknown) => error instanceof ApiError && error.isNetwork;
export async function syncOrganic(provider: OrganicProvider) {
  let synced = 0; let failed = 0;
  for (const entry of read()) {
    try {
      if (entry.op === 'save_profile') organicStorage.saveProfile(await provider.saveProfile(entry.farmId, entry.input, entry.idempotencyKey));
      else organicStorage.addPractice(await provider.createPractice(entry.input));
      organicOutbox.remove(entry.entryId); synced += 1;
    } catch (error) {
      if (isOrganicOfflineError(error)) break;
      // Preserve retryable failures in the durable outbox for the next sync.
      if (!(error instanceof ApiError) || error.status >= 500 || [401, 403, 429].includes(error.status)) {
        failed += 1; break;
      }
      organicOutbox.remove(entry.entryId); failed += 1;
    }
  }
  return { synced, failed, remaining: read().length };
}
