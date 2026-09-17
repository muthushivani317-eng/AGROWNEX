import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

import type { PartnerLinkRequest, PartnerOrgKind, PartnerLinkStatus } from '../types';

/** Raw shape returned by GET /organic-partner/my-link-requests. */
interface RawPartnerLinkRequest {
  id: string;
  organization_name: string;
  organization_kind: PartnerOrgKind;
  status: PartnerLinkStatus;
}

const QUERY_KEY = ['partnerLinks', 'myRequests'] as const;

function toPartnerLinkRequest(row: RawPartnerLinkRequest): PartnerLinkRequest {
  return {
    id: row.id,
    organizationName: row.organization_name,
    organizationKind: row.organization_kind,
    status: row.status,
  };
}

/**
 * Organizations that have requested, or already have, access to this
 * farmer's data. "pending" needs the farmer's approval; "active" can be
 * revoked at any time.
 */
export function useMyPartnerLinks(enabled = true) {
  return useQuery({
    queryKey: QUERY_KEY,
    enabled,
    queryFn: async () => {
      const rows = await api.get<RawPartnerLinkRequest[]>(
        endpoints.partnerLinks.myRequests,
      );
      return rows.map(toPartnerLinkRequest);
    },
  });
}

function invalidate(): void {
  void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
}

export function useApprovePartnerLink() {
  return useMutation({
    mutationFn: (linkId: string) =>
      api.post<{ status: string }>(endpoints.partnerLinks.approve(linkId)),
    onSuccess: invalidate,
  });
}

export function useRevokePartnerLink() {
  return useMutation({
    mutationFn: (linkId: string) =>
      api.post<{ status: string }>(endpoints.partnerLinks.revoke(linkId)),
    onSuccess: invalidate,
  });
}
