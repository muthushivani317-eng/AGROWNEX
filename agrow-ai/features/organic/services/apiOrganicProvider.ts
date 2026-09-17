import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import type { ApiOrganicPractice, ApiOrganicProfile } from '../types';
import { apiToOrganicPractice, apiToOrganicProfile, practiceInputToApi, profileInputToApi } from './organicMapper';
import type { OrganicProvider } from './organicProvider';

export const apiOrganicProvider: OrganicProvider = {
  async getProfile(farmId) {
    try { return apiToOrganicProfile(await api.get<ApiOrganicProfile>(endpoints.organic.profile(farmId))); }
    catch (error: unknown) { if (typeof error === 'object' && error && 'status' in error && error.status === 404) return null; throw error; }
  },
  async saveProfile(farmId, input, idempotencyKey) { return apiToOrganicProfile(await api.put<ApiOrganicProfile>(endpoints.organic.profile(farmId), profileInputToApi(input), { headers: { 'Idempotency-Key': idempotencyKey ?? `organic-profile-${farmId}` } })); },
  async listPractices(farmId) { const rows = await api.get<ApiOrganicPractice[]>(endpoints.organic.practices, { params: { farm_id: farmId } }); return rows.map(apiToOrganicPractice); },
  async createPractice(input) { return apiToOrganicPractice(await api.post<ApiOrganicPractice>(endpoints.organic.practices, practiceInputToApi(input))); },
};
