/**
 * Farmer-facing consent links to partner organizations (FPO / KVK / agri
 * community). Backed by backend/app/modules/organic_mvp/partner_router.py —
 * built first for the organic certification pilot, but the mechanism itself
 * (a stable farmer reference code, a consent-gated link, approve/revoke) is
 * generic and reused here for general FPO monitoring.
 */
export type PartnerLinkStatus = 'pending' | 'join_requested' | 'active' | 'revoked';
export type PartnerOrgKind = 'fpo' | 'kvk' | 'agri_community';

export interface PartnerLinkRequest {
  id: string;
  organizationId: string;
  organizationName: string;
  organizationKind: PartnerOrgKind;
  status: PartnerLinkStatus;
  initiatedBy: 'farmer' | 'organization';
}

export interface PartnerDirectoryEntry {
  id: string;
  name: string;
  kind: Extract<PartnerOrgKind, 'fpo' | 'kvk'>;
  district: string | null;
}
