export type HarvestReadinessState =
  | "not_assessed"
  | "no_verified_readiness_rule"
  | "insufficient_data"
  | "not_ready"
  | "possibly_ready"
  | "awaiting_farmer_confirmation"
  | "farmer_confirmed_ready"
  | "farmer_confirmed_not_ready"
  | "conflicting_evidence";

export interface HarvestReadiness {
  id: string | null;
  farmId: string | null;
  cropCycleId: string | null;
  state: HarvestReadinessState;
  reliability: string;
  evidenceObserved: string[];
  missing: string[];
  conflicts: string[];
  criteriaVersion: string | null;
  farmerConfirmationRequired: boolean;
  pendingSync: boolean;
  cached: boolean;
  updatedAt: string | null;
}

export const fallbackHarvestReadiness = (): HarvestReadiness => ({
  id: null,
  farmId: null,
  cropCycleId: null,
  state: "no_verified_readiness_rule",
  reliability: "unavailable",
  evidenceObserved: [],
  missing: ["verified_readiness_criteria"],
  conflicts: [],
  criteriaVersion: null,
  farmerConfirmationRequired: false,
  pendingSync: false,
  cached: false,
  updatedAt: null,
});

export interface ApiHarvestReadiness {
  id: string;
  farm_id: string;
  crop_cycle_id: string;
  state: HarvestReadinessState;
  version: number;
  criteria_version: string | null;
  evidence_snapshot: {
    reliability?: string;
    evidence_observed?: string[];
    missing?: string[];
    conflicts?: string[];
    farmer_confirmation_required?: boolean;
  };
  pending_sync: boolean;
  updated_at: string;
}

export interface HarvestReadinessHistoryEntry {
  id: string;
  event: string;
  priorState: string | null;
  nextState: string;
  farmerConfirmed: boolean;
  createdAt: string;
}

export interface ApiHarvestReadinessHistoryEntry {
  id: string;
  event: string;
  prior_state: string | null;
  next_state: string;
  farmer_confirmed: boolean;
  created_at: string;
}

export function mapHarvestReadiness(
  dto: ApiHarvestReadiness,
): HarvestReadiness {
  const evidence = dto.evidence_snapshot ?? {};
  return {
    id: dto.id,
    farmId: dto.farm_id,
    cropCycleId: dto.crop_cycle_id,
    state: dto.state,
    reliability: evidence.reliability ?? "unavailable",
    evidenceObserved: evidence.evidence_observed ?? [],
    missing: evidence.missing ?? [],
    conflicts: evidence.conflicts ?? [],
    criteriaVersion: dto.criteria_version,
    farmerConfirmationRequired: evidence.farmer_confirmation_required ?? false,
    pendingSync: dto.pending_sync,
    cached: false,
    updatedAt: dto.updated_at,
  };
}
