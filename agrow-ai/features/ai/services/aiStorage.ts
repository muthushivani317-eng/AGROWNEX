import { appStorage } from '@/lib/storage';
import { useAuthStore } from '@/features/auth/store/authStore';
import type { SupportedLanguage } from '@/types';

import { AI_STORE_KEY } from '../constants';
import type { ChatMessage } from '../types';

/** A conversation persisted locally (local provider + offline history). */
export interface StoredConversation {
  id: string;
  title: string | null;
  language: SupportedLanguage;
  messages: ChatMessage[];
  updatedAt: string;
}

function storageKey(): string {
  return `${AI_STORE_KEY}.${useAuthStore.getState().user?.id ?? 'anonymous'}`;
}

function readAll(): StoredConversation[] {
  return appStorage.getJSON<StoredConversation[]>(storageKey()) ?? [];
}

function writeAll(list: StoredConversation[]): void {
  appStorage.setJSON(storageKey(), list);
}

export const aiStorage = {
  all(): StoredConversation[] {
    return readAll();
  },
  get(id: string): StoredConversation | null {
    return readAll().find((c) => c.id === id) ?? null;
  },
  upsert(conversation: StoredConversation): void {
    const list = readAll();
    const index = list.findIndex((c) => c.id === conversation.id);
    if (index >= 0) list[index] = conversation;
    else list.unshift(conversation);
    writeAll(list);
  },
  remove(id: string): void {
    writeAll(readAll().filter((c) => c.id !== id));
  },
  clear(): void {
    appStorage.remove(storageKey());
  },
};
