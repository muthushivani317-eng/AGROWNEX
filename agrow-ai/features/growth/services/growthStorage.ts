import { appStorage } from '@/lib/storage';

import { GROWTH_SESSION_KEY, GROWTH_STORE_KEY } from '../constants';
import type { GrowthImage, GrowthSession } from '../types';

/** Local growth mirror in MMKV (local provider + offline cache). */
function readImages(): GrowthImage[] {
  return appStorage.getJSON<GrowthImage[]>(GROWTH_STORE_KEY) ?? [];
}

function writeImages(list: GrowthImage[]): void {
  appStorage.setJSON(GROWTH_STORE_KEY, list);
}

function readSessions(): GrowthSession[] {
  return appStorage.getJSON<GrowthSession[]>(GROWTH_SESSION_KEY) ?? [];
}

function writeSessions(list: GrowthSession[]): void {
  appStorage.setJSON(GROWTH_SESSION_KEY, list);
}

function byNewest(a: GrowthImage, b: GrowthImage): number {
  return b.capturedAt.localeCompare(a.capturedAt);
}

export const growthStorage = {
  allImages(): GrowthImage[] {
    return [...readImages()].sort(byNewest);
  },

  imagesForSession(sessionId: string): GrowthImage[] {
    return readImages()
      .filter((i) => i.sessionId === sessionId)
      .sort(byNewest);
  },

  getImage(id: string): GrowthImage | null {
    return readImages().find((i) => i.id === id) ?? null;
  },

  upsertImage(image: GrowthImage): void {
    const list = readImages();
    const index = list.findIndex((i) => i.id === image.id);
    if (index >= 0) list[index] = image;
    else list.unshift(image);
    writeImages(list);
  },

  /** Replace the cache for a set of images (used when caching an API fetch). */
  cacheImages(images: GrowthImage[]): void {
    const incoming = new Set(images.map((i) => i.id));
    const others = readImages().filter((i) => !incoming.has(i.id));
    writeImages([...images, ...others]);
  },

  removeImage(id: string): void {
    writeImages(readImages().filter((i) => i.id !== id));
  },

  sessions(): GrowthSession[] {
    return readSessions();
  },

  getSession(id: string): GrowthSession | null {
    return readSessions().find((s) => s.id === id) ?? null;
  },

  findActiveSession(farmId: string, crop: string | null): GrowthSession | null {
    return (
      readSessions().find(
        (s) =>
          s.farmId === farmId &&
          s.status === 'active' &&
          (!crop || s.crop === crop),
      ) ?? null
    );
  },

  upsertSession(session: GrowthSession): void {
    const list = readSessions();
    const index = list.findIndex((s) => s.id === session.id);
    if (index >= 0) list[index] = session;
    else list.unshift(session);
    writeSessions(list);
  },

  latestSession(farmId?: string | null): GrowthSession | null {
    return (
      readSessions()
        .filter((session) => !farmId || session.farmId === farmId)
        .sort((a, b) =>
        b.updatedAt.localeCompare(a.updatedAt),
        )[0] ?? null
    );
  },

  clear(): void {
    appStorage.remove(GROWTH_STORE_KEY);
    appStorage.remove(GROWTH_SESSION_KEY);
  },
};
