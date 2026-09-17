import { useAuthStore } from '@/features/auth/store/authStore';
import { appStorage } from '@/lib/storage';
import { ORGANIC_PRACTICE_CACHE, ORGANIC_PROFILE_CACHE } from '../constants';
import type { OrganicFarmProfile, OrganicPractice } from '../types';
import type { OrganicPlanBundle } from '../integrationTypes';
const PLAN_CACHE = 'agrowai.organic.plan';

const userId = () => useAuthStore.getState().user?.id ?? null;
const key = (base: string) => { const id = userId(); return id ? `${base}:${encodeURIComponent(id)}` : null; };
const readProfiles = () => { const k = key(ORGANIC_PROFILE_CACHE); return k ? appStorage.getJSON<Record<string, OrganicFarmProfile>>(k) ?? {} : {}; };
const readPractices = () => { const k = key(ORGANIC_PRACTICE_CACHE); return k ? appStorage.getJSON<Record<string, OrganicPractice[]>>(k) ?? {} : {}; };

export const organicStorage = {
  profile(farmId: string) { return readProfiles()[farmId] ?? null; },
  saveProfile(profile: OrganicFarmProfile) { const k = key(ORGANIC_PROFILE_CACHE); if (!k) return; appStorage.setJSON(k, { ...readProfiles(), [profile.farmId]: profile }); },
  practices(farmId: string) { return readPractices()[farmId] ?? []; },
  savePractices(farmId: string, rows: OrganicPractice[]) { const k = key(ORGANIC_PRACTICE_CACHE); if (!k) return; appStorage.setJSON(k, { ...readPractices(), [farmId]: rows }); },
  addPractice(row: OrganicPractice) { this.savePractices(row.farmId, [row, ...this.practices(row.farmId).filter((item) => item.id !== row.id)]); },
  plan(farmId: string) { const k = key(PLAN_CACHE); return k ? (appStorage.getJSON<Record<string, OrganicPlanBundle>>(k) ?? {})[farmId] ?? null : null; },
  savePlan(plan: OrganicPlanBundle) { const k = key(PLAN_CACHE); if (!k) return; const current = appStorage.getJSON<Record<string, OrganicPlanBundle>>(k) ?? {}; appStorage.setJSON(k, { ...current, [plan.farmId]: plan }); },
};
