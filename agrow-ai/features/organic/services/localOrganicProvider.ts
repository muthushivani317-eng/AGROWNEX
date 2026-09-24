import { uuid } from '@/utils/id';
import type { OrganicProvider } from './organicProvider';
import { organicStorage } from './organicStorage';

export const localOrganicProvider: OrganicProvider = {
  async getProfile(farmId) { return organicStorage.profile(farmId); },
  async saveProfile(farmId, input) { const row = { farmId, ...input, transitionStartDate: input.transitionStartDate ?? null, certificationStatus: 'not_claimed' as const, certificationScheme: null, certificationIdentifier: null, planVersion: null, updatedAt: new Date().toISOString(), syncStatus: 'synced' as const }; organicStorage.saveProfile(row); return row; },
  async listPractices(farmId) { return organicStorage.practices(farmId); },
  async createPractice(input) { const now = new Date().toISOString(); const row = { id: uuid(), ...input, notes: input.notes ?? null, quantity: input.quantity ?? null, unit: input.unit ?? null, treatedAreaHectares: input.treatedAreaHectares ?? null, expenseAmountInr: input.expenseAmountInr ?? null, outcomeStatus: input.outcomeStatus ?? 'not_reported' as const, evidence: [], sourceActionId: input.sourceActionId ?? null, createdAt: now, syncStatus: 'synced' as const }; organicStorage.addPractice(row); return row; },
};
