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
  unit: dto.quantity_unit ?? null,
  treatedAreaHectares: dto.treated_area_hectares ?? null,
  expenseAmountInr: dto.expense_amount_inr ?? null,
  outcomeStatus: dto.outcome_status ?? 'not_reported',
  evidence: (dto.evidence ?? []).map((e) => ({
    id: e.id, evidenceType: e.evidence_type, mimeType: e.mime_type ?? null, capturedAt: e.captured_at ?? null,
  })),
  sourceActionId: dto.action_workflow_id ?? null,
  createdAt: dto.created_at, syncStatus: 'synced',
});
export const practiceInputToApi = (input: OrganicPracticeInput) => ({
  farm_id: input.farmId, practice_type: input.type, practice_code: input.type,
  input_reference: input.title, occurred_at: input.occurredAt,
  note: input.notes ?? null, quantity: input.quantity ?? null,
  quantity_unit: input.unit ?? null,
  treated_area_hectares: input.treatedAreaHectares ?? null,
  expense_amount_inr: input.expenseAmountInr ?? null,
  outcome_status: input.outcomeStatus ?? 'not_reported',
  evidence: (input.evidence ?? []).map((e) => ({
    evidence_type: e.evidenceType, upload_attestation_id: e.uploadAttestationId,
    upload_receipt: e.uploadReceipt, captured_at: e.capturedAt ?? null, retention_consent: e.retentionConsent,
  })),
  action_workflow_id: input.sourceActionId ?? null,
  idempotency_key: input.clientRequestId,
});
