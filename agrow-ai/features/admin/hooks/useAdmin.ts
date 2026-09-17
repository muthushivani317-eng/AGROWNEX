import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { adminKeys, DEFAULT_PAGE_SIZE } from '../constants';
import { getAdminProvider } from '../services/adminProvider';
import type {
  AuditFilter,
  Broadcast,
  BroadcastInput,
  CropIntelligenceFilter,
  FarmerFilter,
  ProcurementFilter,
  ProcurementStatus,
} from '../types';

const STALE = 60 * 1000;

function keyOf(obj: Record<string, string | undefined>): string {
  return JSON.stringify(obj);
}

function toRecord(obj: object): Record<string, string | undefined> {
  return obj as Record<string, string | undefined>;
}

/** The caller's admin identity — also the RBAC gate for showing the admin entry. */
export function useAdminMe() {
  return useQuery({
    queryKey: adminKeys.me(),
    queryFn: () => getAdminProvider().me(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useAdminDashboard(enabled = true) {
  return useQuery({
    queryKey: adminKeys.dashboard(),
    queryFn: () => getAdminProvider().dashboard(),
    enabled,
    staleTime: STALE,
  });
}

export function useBusinessDashboard(enabled = true) {
  return useQuery({
    queryKey: ['admin', 'business-dashboard'], enabled,
    queryFn: () => getAdminProvider().businessDashboard(), staleTime: STALE,
  });
}

export function useAdminFarmers(filter: FarmerFilter, page = 1) {
  return useQuery({
    queryKey: adminKeys.farmers(keyOf(toRecord(filter)), page),
    queryFn: () => getAdminProvider().farmers(filter, page, DEFAULT_PAGE_SIZE),
    staleTime: STALE,
  });
}

export function useAdminFarmerDetail(userId: string | undefined) {
  return useQuery({
    queryKey: adminKeys.farmerDetail(userId ?? ''),
    enabled: Boolean(userId),
    queryFn: () => getAdminProvider().farmerDetail(userId as string),
    staleTime: STALE,
  });
}

export function useAdminAnalytics() {
  return useQuery({
    queryKey: adminKeys.analytics(),
    queryFn: () => getAdminProvider().analytics(),
    staleTime: STALE,
  });
}

export function useCropIntelligence(filter: CropIntelligenceFilter) {
  return useQuery({
    queryKey: adminKeys.cropIntelligence(JSON.stringify(filter)),
    queryFn: () => getAdminProvider().cropIntelligence(filter),
    staleTime: STALE,
  });
}

export function useAdminProcurement(filter: ProcurementFilter, page = 1) {
  return useQuery({
    queryKey: adminKeys.procurement(keyOf(toRecord(filter)), page),
    queryFn: () => getAdminProvider().procurement(filter, page, DEFAULT_PAGE_SIZE),
    staleTime: STALE,
  });
}

export function useUpdateProcurementStatus() {
  return useMutation<
    ProcurementStatus,
    unknown,
    { offerId: string; status: ProcurementStatus; note?: string }
  >({
    mutationFn: ({ offerId, status, note }) =>
      getAdminProvider().updateProcurementStatus(offerId, status, note),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'procurement'] });
      void queryClient.invalidateQueries({ queryKey: adminKeys.dashboard() });
      void queryClient.invalidateQueries({ queryKey: ['admin', 'audit'] });
    },
  });
}

export function useUpdateProcurementCase() {
  return useMutation({
    mutationFn: ({ offerId, input }: { offerId: string; input: import('../types').ProcurementCaseInput }) =>
      getAdminProvider().updateProcurementCase(offerId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'procurement'] });
      void queryClient.invalidateQueries({ queryKey: adminKeys.dashboard() });
      void queryClient.invalidateQueries({ queryKey: ['admin', 'audit'] });
    },
  });
}

export function useRevealBuyerContact() {
  return useMutation({
    mutationFn: (offerId: string) => getAdminProvider().revealBuyerContact(offerId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['admin', 'audit'] }),
  });
}

export function useCommerceLedger(offerId: string, enabled = true) {
  return useQuery({
    queryKey: ['admin', 'procurement', offerId, 'ledger'], enabled,
    queryFn: () => getAdminProvider().commerceLedger(offerId), staleTime: STALE,
  });
}

const invalidateLedger = (offerId: string) => {
  void queryClient.invalidateQueries({ queryKey: ['admin', 'procurement', offerId, 'ledger'] });
  void queryClient.invalidateQueries({ queryKey: ['admin', 'business-dashboard'] });
};

export function useRecordPickup(offerId: string) {
  return useMutation({ mutationFn: (input: Record<string, unknown>) => getAdminProvider().recordPickup(offerId, input), onSuccess: () => invalidateLedger(offerId) });
}
export function useRecordTransaction(offerId: string) {
  return useMutation({ mutationFn: (occurredAt: string) => getAdminProvider().recordTransaction(offerId, occurredAt), onSuccess: () => invalidateLedger(offerId) });
}
export function useRecordPayment(offerId: string) {
  return useMutation({ mutationFn: ({ transactionId, input }: { transactionId: string; input: Record<string, unknown> }) => getAdminProvider().recordPayment(transactionId, input), onSuccess: () => invalidateLedger(offerId) });
}
export function useRecordCommission(offerId: string) {
  return useMutation({ mutationFn: ({ transactionId, occurredAt }: { transactionId: string; occurredAt: string }) => getAdminProvider().recordCommission(transactionId, occurredAt), onSuccess: () => invalidateLedger(offerId) });
}

export function useAdminAi() {
  return useQuery({
    queryKey: adminKeys.ai(),
    queryFn: () => getAdminProvider().ai(),
    staleTime: STALE,
  });
}

export function useAdminNotifications(page = 1) {
  return useQuery({
    queryKey: adminKeys.notifications(page),
    queryFn: () => getAdminProvider().notifications(page, DEFAULT_PAGE_SIZE),
    staleTime: STALE,
  });
}

export function useSendBroadcast() {
  return useMutation<Broadcast, unknown, BroadcastInput>({
    mutationFn: (input) => getAdminProvider().sendBroadcast(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'notifications'] });
      void queryClient.invalidateQueries({ queryKey: ['admin', 'audit'] });
    },
  });
}

export function useAdminAudit(filter: AuditFilter, page = 1) {
  return useQuery({
    queryKey: adminKeys.audit(keyOf(toRecord(filter)), page),
    queryFn: () => getAdminProvider().audit(filter, page, DEFAULT_PAGE_SIZE),
    staleTime: STALE,
  });
}
