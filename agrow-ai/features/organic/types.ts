export type OrganicFarmMode = 'conventional' | 'organic_preferred' | 'transitioning' | 'fully_organic';
export type CertificationStatus = 'not_claimed' | 'self_declared' | 'document_submitted' | 'verified' | 'expired' | 'rejected';
export type OrganicPracticeType = 'amendment' | 'seed_treatment' | 'biological_treatment' | 'botanical_spray' | 'trap' | 'mechanical_weeding' | 'mulching' | 'green_manure' | 'crop_rotation' | 'irrigation_drainage' | 'scouting' | 'harvest' | 'custom';
export type OrganicSyncStatus = 'synced' | 'pending';

export interface OrganicFarmProfile {
  farmId: string;
  mode: OrganicFarmMode;
  transitionStartDate: string | null;
  goals: string[];
  preferredPractices: OrganicPracticeType[];
  certificationStatus: CertificationStatus;
  certificationScheme: string | null;
  certificationIdentifier: string | null;
  planVersion: number | null;
  updatedAt: string;
  syncStatus: OrganicSyncStatus;
}

export interface OrganicFarmProfileInput {
  mode: OrganicFarmMode;
  transitionStartDate?: string | null;
  goals: string[];
  preferredPractices: OrganicPracticeType[];
}

export interface OrganicPractice {
  id: string;
  farmId: string;
  type: OrganicPracticeType;
  title: string;
  occurredAt: string;
  notes: string | null;
  quantity: number | null;
  unit: string | null;
  sourceActionId: string | null;
  createdAt: string;
  syncStatus: OrganicSyncStatus;
}

export interface OrganicPracticeInput {
  farmId: string;
  type: OrganicPracticeType;
  title: string;
  occurredAt: string;
  notes?: string | null;
  quantity?: number | null;
  unit?: string | null;
  sourceActionId?: string | null;
  clientRequestId: string;
}

export interface ApiOrganicProfile {
  farm_id: string; mode: OrganicFarmMode; transition_start_date?: string | null;
  goals?: string[]; preferred_practices?: OrganicPracticeType[];
  certification_status?: CertificationStatus; certification_scheme?: string | null;
  certification_identifier?: string | null; plan_version?: number | null; updated_at: string;
}
export interface ApiOrganicPractice {
  id: string; farm_id: string; practice_type: OrganicPracticeType; practice_code: string; input_reference?: string | null;
  occurred_at: string; note?: string | null; quantity?: number | null; quantity_unit?: string | null;
  action_workflow_id?: string | null; created_at: string;
}
