import { appStorage } from '@/lib/storage';

import { FARM_STORE_KEY } from '../constants';
import type { Farm } from '../types';

/**
 * Local farm mirror in MMKV. Acts as the backing store for the offline-first
 * local provider and as an offline cache for the API provider, so the farm list
 * and details remain available without connectivity.
 */
function readAll(): Farm[] {
  return appStorage.getJSON<Farm[]>(FARM_STORE_KEY) ?? [];
}

function writeAll(list: Farm[]): void {
  appStorage.setJSON(FARM_STORE_KEY, list);
}

export const farmStorage = {
  all(): Farm[] {
    return readAll();
  },
  get(id: string): Farm | null {
    return readAll().find((f) => f.id === id) ?? null;
  },
  upsert(farm: Farm): Farm {
    const list = readAll();
    const index = list.findIndex((f) => f.id === farm.id);
    if (index >= 0) list[index] = farm;
    else list.unshift(farm);
    writeAll(list);
    return farm;
  },
  remove(id: string): void {
    writeAll(readAll().filter((f) => f.id !== id));
  },
  replaceAll(list: Farm[]): void {
    writeAll(list);
  },
  clear(): void {
    appStorage.remove(FARM_STORE_KEY);
  },
};
