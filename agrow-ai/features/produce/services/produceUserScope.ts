import { useAuthStore } from '@/features/auth/store/authStore';
import { appStorage } from '@/lib/storage';

export function currentProduceUserId(): string | null {
  return useAuthStore.getState().user?.id ?? null;
}

export function produceScopedKey(base: string, userId: string): string {
  return `${base}:${encodeURIComponent(userId)}`;
}

/** Flat legacy produce data had no owner metadata and is unsafe on shared devices. */
export function discardUnscopedProduceData(...keys: string[]): void {
  for (const key of keys) {
    if (appStorage.getString(key) !== null) appStorage.remove(key);
  }
}
