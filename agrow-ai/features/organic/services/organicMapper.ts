import type { ApiOrganicPractice, ApiOrganicProfile, OrganicFarmProfile, OrganicFarmProfileInput, OrganicPractice, OrganicPracticeInput } from '../types';

export const apiToOrganicProfile = (dto: ApiOrganicProfile): OrganicFarmProfile => ({
  farmId: dto.farm_id, mode: dto.mode, transitionStartDate: dto.transition_start_date ?? null,
  goals: dto.goals ?? [], preferredPractices: dto.preferred_practices ?? [],
  certificationStatus: dto.certification_status ?? 'not_claimed',
  certificationScheme: dto.certification_scheme ?? null,
  certificationIdentifier: dto.certification_identifier ?? null,
  planVersion: dto.plan_version ?? null, updatedAt: dto.updated_at, syncStatus: 'synced',
});
export const profileInputToApi = (input: OrganicFarmProfileInput) => ({
  mode: input.mode, transition_start_date: input.transitionStartDate ?? null,
  goals: input.goals, preferred_practices: input.preferredPractices,
});
export const apiToOrganicPractice = (dto: ApiOrganicPractice): OrganicPractice => ({
  id: dto.id, farmId: dto.farm_id, type: dto.practice_type,
  title: dto.input_reference ?? dto.practice_code,
  occurredAt: dto.occurred_at, notes: dto.note ?? null, quantity: dto.quantity ?? null,
  unit: dto.quantity_unit ?? null, sourceActionId: dto.action_workflow_id ?? null,
  createdAt: dto.created_at, syncStatus: 'synced',
});
export const practiceInputToApi = (input: OrganicPracticeInput) => ({
  farm_id: input.farmId, practice_type: input.type, practice_code: input.type,
  input_reference: input.title, occurred_at: input.occurredAt,
  note: input.notes ?? null, quantity: input.quantity ?? null,
  quantity_unit: input.unit ?? null, action_workflow_id: input.sourceActionId ?? null,
  idempotency_key: input.clientRequestId,
});
