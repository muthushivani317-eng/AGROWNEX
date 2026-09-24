import { useMutation, useQuery } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { uuid } from '@/utils/id';
import { organicKeys } from '../constants';
import { getOrganicProvider } from '../services/organicProvider';
import { organicStorage } from '../services/organicStorage';
import { isOrganicOfflineError, organicOutbox } from '../services/organicSync';
import { uploadOrganicEvidence } from '../services/organicEvidenceApi';
import type { OrganicFarmProfileInput, OrganicPracticeInput } from '../types';

export function useOrganicProfile(farmId: string) {
  return useQuery({ queryKey: organicKeys.profile(farmId), queryFn: async () => {
    try { const row = await getOrganicProvider().getProfile(farmId); if (row) organicStorage.saveProfile(row); return row; }
    catch (error) { const cached = organicStorage.profile(farmId); if (isOrganicOfflineError(error) && cached) return cached; throw error; }
  }});
}
export function useSaveOrganicProfile(farmId: string) {
  return useMutation({ mutationFn: async (input: OrganicFarmProfileInput) => {
    const idempotencyKey = uuid();
    try { const profile = await getOrganicProvider().saveProfile(farmId, input, idempotencyKey); organicStorage.saveProfile(profile); return { profile, offline: false }; }
    catch (error) { if (!isOrganicOfflineError(error)) throw error; const profile = { farmId, ...input, transitionStartDate: input.transitionStartDate ?? null, certificationStatus: 'not_claimed' as const, certificationScheme: null, certificationIdentifier: null, planVersion: null, updatedAt: new Date().toISOString(), syncStatus: 'pending' as const }; organicStorage.saveProfile(profile); organicOutbox.enqueue({ op: 'save_profile', farmId, input, idempotencyKey }); return { profile, offline: true }; }
  }, onSuccess: () => void queryClient.invalidateQueries({ queryKey: organicKeys.profile(farmId) }) });
}
export function useOrganicPractices(farmId: string) {
  return useQuery({ queryKey: organicKeys.practices(farmId), queryFn: async () => {
    try { const rows = await getOrganicProvider().listPractices(farmId); organicStorage.savePractices(farmId, rows); return rows; }
    catch (error) { const cached = organicStorage.practices(farmId); if (isOrganicOfflineError(error)) return cached; throw error; }
  }});
}
/**
 * Uploads one piece of Farm Diary evidence (currently: a photo) and returns
 * the attestation id + signed receipt needed by useCreateOrganicPractice's
 * `evidence` array. Requires connectivity -- unlike practice creation, this
 * is not queued offline (a photo can't be attested without actually
 * reaching the backend), so callers should surface the mutation's error to
 * the farmer and let them retry once online.
 */
export function useUploadOrganicEvidence(farmId: string) {
  return useMutation({
    mutationFn: (input: { fileUri: string; mimeType: string }) =>
      uploadOrganicEvidence(farmId, input.fileUri, input.mimeType),
  });
}

export function useCreateOrganicPractice(farmId: string) {
  return useMutation({ mutationFn: async (input: Omit<OrganicPracticeInput, 'farmId' | 'clientRequestId'>) => {
    const payload = { ...input, farmId, clientRequestId: uuid() };
    try { const practice = await getOrganicProvider().createPractice(payload); organicStorage.addPractice(practice); return { practice, offline: false }; }
    catch (error) { if (!isOrganicOfflineError(error)) throw error; const practice = { id: payload.clientRequestId, ...payload, notes: payload.notes ?? null, quantity: payload.quantity ?? null, unit: payload.unit ?? null, treatedAreaHectares: payload.treatedAreaHectares ?? null, expenseAmountInr: payload.expenseAmountInr ?? null, outcomeStatus: payload.outcomeStatus ?? 'not_reported' as const, evidence: [], sourceActionId: payload.sourceActionId ?? null, createdAt: new Date().toISOString(), syncStatus: 'pending' as const }; organicStorage.addPractice(practice); organicOutbox.enqueue({ op: 'create_practice', farmId, input: payload }); return { practice, offline: true }; }
  }, onSuccess: () => void queryClient.invalidateQueries({ queryKey: organicKeys.practices(farmId) }) });
}
