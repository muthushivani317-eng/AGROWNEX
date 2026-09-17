import { appStorage } from '@/lib/storage';

import {
  CONSULTATION_CACHE_KEY,
  CONSULTATION_LOCAL_KEY,
  EXPERTS_CACHE_KEY,
  EXPERTS_LOCAL_KEY,
} from '../constants';
import type {
  Consultation,
  ConsultationDetail,
  Expert,
  ExpertDetail,
} from '../types';

/**
 * Local Expert Connect store in MMKV:
 *  - an offline **cache** of the last-seen API expert/consultation lists,
 *  - the **local-provider** experts + consultations (used in dev / without a backend).
 */
interface ListCache<T> {
  [key: string]: { items: T[]; cachedAt: string };
}

function read<T>(key: string): T {
  return (appStorage.getJSON<T>(key) ?? {}) as T;
}

export const expertStorage = {
  // --- Offline cache (API provider) ---
  cacheExpertList(key: string, items: Expert[]): void {
    const cache = read<ListCache<Expert>>(EXPERTS_CACHE_KEY);
    cache[key] = { items, cachedAt: new Date().toISOString() };
    appStorage.setJSON(EXPERTS_CACHE_KEY, cache);
  },
  getCachedExpertList(key: string): Expert[] | null {
    return read<ListCache<Expert>>(EXPERTS_CACHE_KEY)[key]?.items ?? null;
  },
  cacheConsultationList(key: string, items: Consultation[]): void {
    const cache = read<ListCache<Consultation>>(CONSULTATION_CACHE_KEY);
    cache[key] = { items, cachedAt: new Date().toISOString() };
    appStorage.setJSON(CONSULTATION_CACHE_KEY, cache);
  },
  getCachedConsultationList(key: string): Consultation[] | null {
    return read<ListCache<Consultation>>(CONSULTATION_CACHE_KEY)[key]?.items ?? null;
  },

  // --- Local provider store: experts ---
  hasLocalExperts(): boolean {
    return Object.keys(read<Record<string, ExpertDetail>>(EXPERTS_LOCAL_KEY)).length > 0;
  },
  localExperts(): ExpertDetail[] {
    return Object.values(read<Record<string, ExpertDetail>>(EXPERTS_LOCAL_KEY));
  },
  getLocalExpert(id: string): ExpertDetail | null {
    return read<Record<string, ExpertDetail>>(EXPERTS_LOCAL_KEY)[id] ?? null;
  },
  seedLocalExperts(experts: ExpertDetail[]): void {
    const map: Record<string, ExpertDetail> = {};
    experts.forEach((e) => {
      map[e.id] = e;
    });
    appStorage.setJSON(EXPERTS_LOCAL_KEY, map);
  },

  // --- Local provider store: consultations ---
  localConsultations(): ConsultationDetail[] {
    return Object.values(
      read<Record<string, ConsultationDetail>>(CONSULTATION_LOCAL_KEY),
    ).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  },
  getLocalConsultation(id: string): ConsultationDetail | null {
    return read<Record<string, ConsultationDetail>>(CONSULTATION_LOCAL_KEY)[id] ?? null;
  },
  upsertLocalConsultation(consultation: ConsultationDetail): void {
    const map = read<Record<string, ConsultationDetail>>(CONSULTATION_LOCAL_KEY);
    map[consultation.id] = consultation;
    appStorage.setJSON(CONSULTATION_LOCAL_KEY, map);
  },

  clear(): void {
    appStorage.remove(EXPERTS_CACHE_KEY);
    appStorage.remove(CONSULTATION_CACHE_KEY);
    appStorage.remove(EXPERTS_LOCAL_KEY);
    appStorage.remove(CONSULTATION_LOCAL_KEY);
  },
};

export function expertListKey(params: Record<string, unknown>): string {
  return [
    params.category ?? '',
    params.crop ?? '',
    params.district ?? '',
    params.language ?? '',
    params.expertType ?? '',
    params.search ?? '',
    params.page ?? 1,
  ]
    .join('|')
    .toLowerCase();
}

export function consultationListKey(view: string, params: Record<string, unknown>): string {
  return [view, params.status ?? '', params.category ?? '', params.page ?? 1]
    .join('|')
    .toLowerCase();
}
