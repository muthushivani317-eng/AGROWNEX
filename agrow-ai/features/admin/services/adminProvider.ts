import { buildProfile, isBackendConfigured } from '@/config/env';
import { mayUseLocalFeatureMocks } from '@/config/providerSafety';
import { logger } from '@/lib/logger';

import type {
  AdminAnalytics,
  AdminDashboard,
  BusinessDashboard,
  CropIntelligence,
  CropIntelligenceFilter,
  CommerceLedger,
  AdminMe,
  AiMonitoring,
  AuditFilter,
  AuditRow,
  Broadcast,
  BroadcastInput,
  FarmerDetail,
  FarmerFilter,
  FarmerRow,
  NotificationsOverview,
  Paginated,
  ProcurementFilter,
  ProcurementCaseInput,
  ProcurementRow,
  ProcurementStatus,
  ProcurementView,
} from '../types';

/**
 * Admin platform data source contract. Backed by the AgrowAI admin API (RBAC,
 * auditing and cross-module aggregation run server-side) when a backend is configured,
 * otherwise a local provider that serves clearly-flagged sample data so the team
 * dashboard is explorable in development. Future admin roles / enterprise / export
 * dashboards plug in behind this seam with no screen change.
 */
export interface AdminProvider {
  me(): Promise<AdminMe>;
  dashboard(): Promise<AdminDashboard>;
  businessDashboard(): Promise<BusinessDashboard>;
  farmers(
    filter?: FarmerFilter,
    page?: number,
    pageSize?: number,
  ): Promise<Paginated<FarmerRow>>;
  farmerDetail(userId: string): Promise<FarmerDetail>;
  analytics(): Promise<AdminAnalytics>;
  cropIntelligence(filter?: CropIntelligenceFilter): Promise<CropIntelligence>;
  procurement(
    filter?: ProcurementFilter,
    page?: number,
    pageSize?: number,
  ): Promise<ProcurementView>;
  updateProcurementStatus(
    offerId: string,
    status: ProcurementStatus,
    note?: string,
  ): Promise<ProcurementStatus>;
  updateProcurementCase(offerId: string, input: ProcurementCaseInput): Promise<ProcurementRow>;
  revealBuyerContact(offerId: string): Promise<string>;
  commerceLedger(offerId: string): Promise<CommerceLedger>;
  recordPickup(offerId: string, input: Record<string, unknown>): Promise<void>;
  recordTransaction(offerId: string, occurredAt: string): Promise<{ id: string }>;
  recordPayment(transactionId: string, input: Record<string, unknown>): Promise<void>;
  recordCommission(transactionId: string, occurredAt: string): Promise<void>;
  ai(): Promise<AiMonitoring>;
  notifications(page?: number, pageSize?: number): Promise<NotificationsOverview>;
  sendBroadcast(input: BroadcastInput): Promise<Broadcast>;
  audit(filter?: AuditFilter, page?: number, pageSize?: number): Promise<Paginated<AuditRow>>;
}

export class AdminError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'AdminError';
  }
}

/** True when an error means the caller may not view this resource (RBAC). */
export function isAccessError(error: unknown): error is AdminError {
  return (
    error instanceof AdminError &&
    (error.code === 'forbidden' || error.code === 'permission_denied')
  );
}

let provider: AdminProvider | null = null;

export function getAdminProvider(): AdminProvider {
  if (provider) return provider;
  if (isBackendConfigured) {
    provider = require('./apiAdminProvider').apiAdminProvider as AdminProvider;
    logger.info('admin', 'using api provider');
  } else if (mayUseLocalFeatureMocks(buildProfile, isBackendConfigured)) {
    provider = require('./localAdminProvider').localAdminProvider as AdminProvider;
    logger.info('admin', 'using local provider');
  } else {
    throw new AdminError(
      'configuration_required',
      'The Admin API is not configured. Release builds never use sample admin data.',
    );
  }
  return provider;
}

/** Test seam: force a provider (used to reset between tests). */
export function _setAdminProvider(next: AdminProvider | null): void {
  provider = next;
}
