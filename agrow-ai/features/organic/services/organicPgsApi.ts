import { httpClient } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

/**
 * Client for backend/app/modules/organic_mvp's farmer-facing PGS
 * (Participatory Guarantee System) endpoints -- Certification Companion,
 * blueprint Phase 6. Same raw-payload convention as organicReadinessApi.ts
 * (organic_mvp does not use the { success, data } envelope), so this goes
 * through httpClient directly.
 *
 * Deliberately does NOT expose anything that writes a verified certificate
 * or a PGS state transition -- that only happens via
 * POST /admin/organic-mvp/farms/{farm_id}/pgs/review, gated to an
 * agriculture-officer/owner/super-admin role (backend/app/modules/
 * organic_mvp/router.py::review_pgs). A farmer or peer can only ever
 * submit evidence/checklist input for a human reviewer to act on --
 * mirrors "pre-certification never displays as certified" and "no
 * self-assigned PGS labels" from the blueprint's blocking checklist.
 */

export const PGS_CHECKLIST_KEYS = [
  'whole_holding_reviewed',
  'conversion_plan_recorded',
  'conversion_completed',
  'no_major_non_compliance',
] as const;
export type PgsChecklistKey = (typeof PGS_CHECKLIST_KEYS)[number];

export type PgsState =
  | 'pre_certification_trial'
  | 'pgs_eligibility_review'
  | 'regional_council_approval_required'
  | 'pgs_registration_pending'
  | 'pgs_green_under_conversion'
  | 'pgs_organic'
  | 'non_compliance_review';

export interface PgsAppraisalSummary {
  id: string;
  scheduled_on: string;
  status: 'scheduled' | 'completed';
}

export interface PgsStatusResponse {
  state: PgsState;
  notice: string | null;
  partial_conversion: boolean;
  checklist: Partial<Record<PgsChecklistKey, boolean>>;
  certificate_id: string | null;
  issuing_authority: string | null;
  valid_to: string | null;
  appraisals: PgsAppraisalSummary[];
}

export interface PgsChecklistInput {
  partial_conversion: boolean;
  checklist: Partial<Record<PgsChecklistKey, boolean>>;
}

export interface PgsPeerAssignment {
  id: string;
  case_id: string;
  farm_id: string | null;
  farm_name: string | null;
  scheduled_on: string;
  status: 'scheduled' | 'completed';
}

export const organicPgsApi = {
  async getStatus(farmId: string): Promise<PgsStatusResponse> {
    const response = await httpClient.get<PgsStatusResponse>(
      endpoints.organicMvp.pgsStatus(farmId),
    );
    return response.data;
  },

  async updateChecklist(
    farmId: string,
    input: PgsChecklistInput,
  ): Promise<{ state: PgsState } | PgsStatusResponse> {
    const response = await httpClient.put(
      endpoints.organicMvp.pgsChecklist(farmId),
      input,
    );
    return response.data;
  },

  async listPeerAssignments(): Promise<PgsPeerAssignment[]> {
    const response = await httpClient.get<PgsPeerAssignment[]>(
      endpoints.organicMvp.pgsPeerAssignments,
    );
    return response.data;
  },

  async submitPeerAppraisal(
    appraisalId: string,
    note: string,
  ): Promise<{ status: 'completed' }> {
    const response = await httpClient.post(
      endpoints.organicMvp.pgsPeerAssignmentSubmit(appraisalId),
      { findings: { note }, complete: true },
    );
    return response.data;
  },
};
