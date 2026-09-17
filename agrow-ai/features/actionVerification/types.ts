export type ActionVerificationStatus =
  | "suggested"
  | "viewed"
  | "farmer_reported_done"
  | "farmer_reported_not_done"
  | "deferred"
  | "corrected"
  | "cancelled"
  | "expired"
  | "skipped"
  | "unable_to_complete";

export const actionStatusLabelKey = (
  status: ActionVerificationStatus,
): string => `actionVerification.status.${status}`;

/**
 * Maps a submit failure to the right copy instead of always showing
 * "networkError" -- previously every submit failure (an actual offline/
 * network drop, a version conflict from a concurrent update, an expired
 * action) showed the same generic network-error text, which is misleading
 * for a version conflict or expiry (found in the 2026-08 pre-release
 * audit). Accepts `unknown` since a caught error's type isn't guaranteed.
 */
export function submitErrorMessageKey(error: unknown): string {
  const err = error as { status?: number; errorCode?: string } | null;
  if (err?.status === 409 && err.errorCode === "ACTION_VERSION_CONFLICT") {
    return "actionVerification.versionConflict";
  }
  if (err?.status === 409 && err.errorCode === "ACTION_EXPIRED") {
    return "actionVerification.actionExpired";
  }
  return "actionVerification.networkError";
}

export interface ActionVerification {
  id: string;
  farmId: string;
  cropCycleId: string | null;
  sourceFeature: string;
  sourceRecordId: string;
  actionCode: string;
  suggestionTime: string;
  status: ActionVerificationStatus;
  version: number;
  expiresAt: string | null;
  pendingSync: boolean;
  updatedAt: string;
}

export interface ApiActionVerification {
  id: string;
  farm_id: string;
  crop_cycle_id: string | null;
  source_feature: string;
  source_record_id: string;
  source_version: string;
  action_code: string;
  source_verified: boolean;
  farmer_created: boolean;
  suggestion_time: string;
  due_at: string | null;
  expires_at: string | null;
  status: ActionVerificationStatus;
  verification_scope: "workflow_completion_only";
  version: number;
  pending_sync: boolean;
  created_at: string;
  updated_at: string;
}
