/**
 * Farmer-facing consent links to partner organizations (FPO / KVK / agri
 * community). Backed by backend/app/modules/organic_mvp/partner_router.py —
 * built first for the organic certification pilot, but the mechanism itself
 * (a stable farmer reference code, a consent-gated link, approve/revoke) is
 * generic and reused here for general FPO monitoring.
 */
export type PartnerLinkStatus = 'pending' | 'active' | 'revoked';
export type PartnerOrgKind = 'fpo' | 'kvk' | 'agri_community';

export interface PartnerLinkRequest {
  id: string;
  organizationName: string;
  organizationKind: PartnerOrgKind;
  status: PartnerLinkStatus;
}
