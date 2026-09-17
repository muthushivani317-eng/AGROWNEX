import type { AdminRole, AdminStatus, ProcurementStatus } from './types';

export const DEFAULT_PAGE_SIZE = 20;

/** React Query keys for the admin platform. */
export const adminKeys = {
  all: ['admin'] as const,
  me: () => ['admin', 'me'] as const,
  dashboard: () => ['admin', 'dashboard'] as const,
  farmers: (filterKey: string, page: number) =>
    ['admin', 'farmers', filterKey, page] as const,
  farmerDetail: (id: string) => ['admin', 'farmer', id] as const,
  analytics: () => ['admin', 'analytics'] as const,
  cropIntelligence: (filterKey: string) => ['admin', 'crop-intelligence', filterKey] as const,
  procurement: (filterKey: string, page: number) =>
    ['admin', 'procurement', filterKey, page] as const,
  ai: () => ['admin', 'ai'] as const,
  notifications: (page: number) => ['admin', 'notifications', page] as const,
  announcements: (page: number) => ['admin', 'announcements', page] as const,
  audit: (filterKey: string, page: number) => ['admin', 'audit', filterKey, page] as const,
};

/** The overview cards on the dashboard, in the documented backend order. */
export const OVERVIEW_LABEL_KEY: Record<string, string> = {
  total_farmers: 'admin.metric.totalFarmers',
  total_farms: 'admin.metric.totalFarms',
  active_users: 'admin.metric.activeUsers',
  today_ai_chats: 'admin.metric.todayAiChats',
  disease_reports: 'admin.metric.diseaseReports',
  soil_reports: 'admin.metric.soilReports',
  satellite_reports: 'admin.metric.satelliteReports',
  intelligence_reports: 'admin.metric.intelligenceReports',
  scheme_saves: 'admin.metric.schemeSaves',
  produce_listings: 'admin.metric.produceListings',
  expert_consultations: 'admin.metric.expertConsultations',
  notifications_sent: 'admin.metric.notificationsSent',
};

export const ROLE_LABEL_KEY: Record<AdminRole, string> = {
  owner: 'admin.role.owner',
  super_admin: 'admin.role.superAdmin',
  district_manager: 'admin.role.districtManager',
  procurement_manager: 'admin.role.procurementManager',
  agriculture_officer: 'admin.role.agricultureOfficer',
  customer_support: 'admin.role.customerSupport',
};

export const STATUS_LABEL_KEY: Record<AdminStatus, string> = {
  active: 'admin.status.active',
  suspended: 'admin.status.suspended',
};

/** The procurement pipeline in order, with a chip tone per stage. */
export const PROCUREMENT_STATUSES: ProcurementStatus[] = [
  'new',
  'under_review',
  'farmer_contacted',
  'finding_buyers',
  'buyer_interested',
  'offer_received',
  'farmer_approval_pending',
  'cancelled',
];

export const PROCUREMENT_LABEL_KEY: Record<ProcurementStatus, string> = {
  new: 'admin.procurementStatus.new',
  under_review: 'admin.procurementStatus.underReview',
  farmer_contacted: 'admin.procurementStatus.farmerContacted',
  finding_buyers: 'admin.procurementStatus.findingBuyers',
  buyer_interested: 'admin.procurementStatus.buyerInterested',
  offer_received: 'admin.procurementStatus.offerReceived',
  farmer_approval_pending: 'admin.procurementStatus.farmerApprovalPending',
  farmer_accepted: 'admin.procurementStatus.farmerAccepted',
  farmer_rejected: 'admin.procurementStatus.farmerRejected',
  cancelled: 'admin.procurementStatus.cancelled',
};

export const PROCUREMENT_TONE: Record<
  ProcurementStatus,
  'neutral' | 'info' | 'warning' | 'success' | 'danger' | 'primary'
> = {
  new: 'neutral',
  under_review: 'info',
  farmer_contacted: 'info',
  finding_buyers: 'warning',
  buyer_interested: 'warning',
  offer_received: 'primary',
  farmer_approval_pending: 'primary',
  farmer_accepted: 'success',
  farmer_rejected: 'danger',
  cancelled: 'danger',
};

export const BROADCAST_STATUS_TONE: Record<
  string,
  'neutral' | 'info' | 'warning' | 'success' | 'danger'
> = {
  draft: 'neutral',
  queued: 'info',
  sent: 'success',
  failed: 'danger',
};

export const BROADCAST_TARGET_TYPES = ['all', 'village', 'district', 'crop', 'language'] as const;

export const BROADCAST_TARGET_LABEL_KEY: Record<string, string> = {
  all: 'admin.target.all',
  village: 'admin.target.village',
  district: 'admin.target.district',
  crop: 'admin.target.crop',
  language: 'admin.target.language',
};

/** Analytics sections rendered on the Analytics screen (label + data key). */
export const ANALYTICS_SECTIONS: { key: keyof AnalyticsSectionMap; labelKey: string }[] = [
  { key: 'cropDistribution', labelKey: 'admin.analytics.crops' },
  { key: 'diseaseDistribution', labelKey: 'admin.analytics.diseases' },
  { key: 'nutrientDeficiencies', labelKey: 'admin.analytics.nutrients' },
  { key: 'soilCategories', labelKey: 'admin.analytics.soil' },
  { key: 'expertTrends', labelKey: 'admin.analytics.experts' },
  { key: 'produceByCrop', labelKey: 'admin.analytics.produce' },
];

export interface AnalyticsSectionMap {
  cropDistribution: unknown;
  diseaseDistribution: unknown;
  nutrientDeficiencies: unknown;
  soilCategories: unknown;
  expertTrends: unknown;
  produceByCrop: unknown;
}
