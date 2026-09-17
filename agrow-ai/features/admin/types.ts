/**
 * Admin platform — the AgrowAI team dashboard (NOT a farmer interface).
 *
 * Read-only operational visibility over every module plus farmer management,
 * procurement, AI monitoring, analytics, broadcasts, content and the immutable audit
 * trail. Untracked metrics stay `null` and are surfaced honestly — never fabricated
 * (docs/PRODUCT_RULES.md). Client-side camelCase mirror of the backend schemas.
 */

export type AdminRole =
  | 'owner'
  | 'super_admin'
  | 'district_manager'
  | 'procurement_manager'
  | 'agriculture_officer'
  | 'customer_support';

export type AdminStatus = 'active' | 'suspended';

export type ProcurementStatus =
  | 'new'
  | 'under_review'
  | 'farmer_contacted'
  | 'finding_buyers'
  | 'buyer_interested'
  | 'offer_received'
  | 'farmer_approval_pending'
  | 'farmer_accepted'
  | 'farmer_rejected'
  | 'cancelled';

export type BroadcastTargetType = 'all' | 'village' | 'district' | 'crop' | 'language';
export type BroadcastScheduleType = 'immediate' | 'scheduled';
export type BroadcastStatus = 'draft' | 'queued' | 'sent' | 'failed';

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

// --------------------------------------------------------------------------- //
// Identity
// --------------------------------------------------------------------------- //
export interface AdminMe {
  id: string;
  userId: string;
  role: AdminRole;
  fullName: string | null;
  permissions: string[];
  status: AdminStatus;
  /** Client-only: resolved from a local (dev / no-backend) sample admin. */
  isSample?: boolean;
}

// --------------------------------------------------------------------------- //
// Dashboard
// --------------------------------------------------------------------------- //
export interface OverviewCard {
  key: string;
  value: number | null;
}

export interface AdminDashboard {
  cards: OverviewCard[];
  procurementStatusCounts: Record<string, number>;
  generatedAt: string;
  isSample?: boolean;
}

// --------------------------------------------------------------------------- //
// Farmer management
// --------------------------------------------------------------------------- //
export interface FarmerRow {
  userId: string;
  farmerRef?: string;
  fullName: string | null;
  phoneNumber: string | null;
  district: string | null;
  village: string | null;
  primaryCrop: string | null;
  language: string | null;
  farmCount: number;
  createdAt: string | null;
}

export interface FarmSummary {
  id: string;
  name: string;
  crop: string | null;
  areaHectares: number | null;
  status: string;
  createdAt: string;
}

export interface FarmerDetail {
  userId: string;
  farmerRef?: string;
  fullName: string | null;
  phoneNumber: string | null;
  district: string | null;
  block: string | null;
  village: string | null;
  primaryCrop: string | null;
  language: string | null;
  farms: FarmSummary[];
  counts: Record<string, number>;
}

export interface FarmerFilter {
  search?: string;
  district?: string;
  crop?: string;
}

// --------------------------------------------------------------------------- //
// Analytics
// --------------------------------------------------------------------------- //
export interface DistributionItem {
  label: string;
  count: number;
}

export interface AdminAnalytics {
  farmerGrowth: DistributionItem[];
  cropDistribution: DistributionItem[];
  diseaseDistribution: DistributionItem[];
  nutrientDeficiencies: DistributionItem[];
  soilCategories: DistributionItem[];
  expertTrends: DistributionItem[];
  produceByCrop: DistributionItem[];
  isSample?: boolean;
}

export interface CropIntelligenceFilter {
  crop?: string;
  district?: string;
  village?: string;
  harvestDays?: number;
}

export interface CropIntelligenceGroup {
  label: string;
  farmCount: number;
  farmerCount: number;
  knownAreaHectares: number;
  farmsWithArea: number;
}

export interface CropIntelligence {
  generatedAt: string;
  filters: CropIntelligenceFilter;
  summary: {
    farmerCount: number;
    farmCount: number;
    knownAreaHectares: number;
    farmsWithArea: number;
    farmsWithoutArea: number;
    recordedStageFarms: number;
    saleListingCount: number;
    harvestWindowFarmerCount: number;
    harvestWindowListingCount: number;
  };
  byCrop: CropIntelligenceGroup[];
  byLocation: CropIntelligenceGroup[];
  cropStages: { label: string; farmCount: number }[];
  offeredQuantities: { unit: string; quantity: number }[];
  harvestWindow: {
    fromDate: string;
    toDate: string;
    farmerCount: number;
    listingCount: number;
  };
  isSample?: boolean;
}

// --------------------------------------------------------------------------- //
// Procurement
// --------------------------------------------------------------------------- //
export interface ProcurementRow {
  offerId: string;
  listingRef?: string;
  farmerRef?: string;
  crop: string | null;
  variety: string | null;
  quantity: number;
  unit: string;
  expectedGrade: string | null;
  harvestDate: string | null;
  village: string | null;
  district: string | null;
  farmerName: string | null;
  offerStatus: string;
  adminStatus: ProcurementStatus;
  assignedAdminId: string | null;
  followUpAt: string | null;
  buyerName: string | null;
  buyerContact: string | null;
  buyerContactMasked: boolean;
  cultivatedAreaHectares: number | null;
  expectedTotalQuantity: number | null;
  availableQuantity: number | null;
  quantityProvenance: string | null;
  qualityNotes: string | null;
  buyerOfferQuantity: number | null;
  buyerOfferPrice: number | null;
  transportCost: number | null;
  commissionRate: number | null;
  negotiationNotes: string | null;
}

export interface ProcurementCaseInput {
  status?: ProcurementStatus;
  assignedAdminId?: string | null;
  followUpAt?: string | null;
  buyerName?: string | null;
  buyerContact?: string | null;
  buyerOfferQuantity?: number | null;
  buyerOfferPrice?: number | null;
  transportCost?: number | null;
  commissionRate?: number | null;
  currency?: string | null;
  priceUnit?: string | null;
  negotiationNotes?: string | null;
}

export interface CommerceLedger {
  offer_id: string;
  case_status: string;
  transaction: null | { id: string; quantity: number; unit_price: string; gross_amount: string; currency: string; occurred_at: string };
  pickups: { id: string; status: string; scheduled_at: string | null; occurred_at: string | null; location: string | null; note: string | null; created_at: string }[];
  payments: { id: string; entry_type: string; amount: string; currency: string; reference: string | null; occurred_at: string }[];
  commissions: { id: string; entry_type: string; base_amount: string; rate: string; amount: string; currency: string; occurred_at: string }[];
}

export interface BusinessDashboard {
  generated_at: string;
  total_farmers: number;
  new_farmers_today: number;
  active_farmers_today: number;
  active_farmers_7d: number;
  active_farmers_30d: number;
  produce_listings_today: number;
  procurement_status_counts: Record<string, number>;
  transactions: number;
  gmv: string;
  buyer_receipts: string;
  payment_outstanding: string;
  earned_commission: string;
  currency: string;
}

export interface ProcurementBucket {
  label: string;
  count: number;
  quantityKg: number;
}

export interface QuantityTrendPoint {
  label: string;
  quantityKg: number;
  count: number;
}

export interface ProcurementAnalytics {
  byVillage: ProcurementBucket[];
  byCrop: ProcurementBucket[];
  bySeason: ProcurementBucket[];
  quantityTrend: QuantityTrendPoint[];
  totalOffers: number;
  totalQuantityKg: number;
}

export interface ProcurementView {
  page: Paginated<ProcurementRow>;
  analytics: ProcurementAnalytics;
  isSample?: boolean;
}

export interface ProcurementFilter {
  crop?: string;
  village?: string;
  district?: string;
  search?: string;
}

// --------------------------------------------------------------------------- //
// AI monitoring
// --------------------------------------------------------------------------- //
export interface DailyPoint {
  label: string;
  count: number;
}

export interface AiMonitoring {
  todayRequests: number | null;
  totalMessages: number | null;
  diseaseDetections: number | null;
  nutrientAnalyses: number | null;
  satelliteAnalyses: number | null;
  memoryGenerated: number | null;
  intelligenceReports: number | null;
  averageConfidence: number | null;
  dailyRequests: DailyPoint[];
  modelLatencyMs: number | null;
  apiFailures: number | null;
  isSample?: boolean;
}

// --------------------------------------------------------------------------- //
// Broadcast / notifications
// --------------------------------------------------------------------------- //
export interface Broadcast {
  id: string;
  title: string;
  body: string;
  language: string;
  targetType: BroadcastTargetType;
  targetValue: string | null;
  scheduleType: BroadcastScheduleType;
  status: BroadcastStatus;
  recipientCount: number;
  deliveredCount: number;
  scheduledFor: string | null;
  sentAt: string | null;
  createdAt: string;
  isSample?: boolean;
}

export interface NotificationsOverview {
  broadcasts: Paginated<Broadcast>;
  deliveredTotal: number;
  isSample?: boolean;
}

export interface BroadcastInput {
  title: string;
  body: string;
  language: string;
  targetType: BroadcastTargetType;
  targetValue?: string | null;
  scheduleType: BroadcastScheduleType;
  scheduledFor?: string | null;
}

// --------------------------------------------------------------------------- //
// Audit
// --------------------------------------------------------------------------- //
export interface AuditRow {
  id: string;
  adminId: string | null;
  role: string | null;
  action: string;
  target: string | null;
  targetId: string | null;
  ipAddress: string | null;
  meta: Record<string, unknown> | null;
  createdAt: string;
}

export interface AuditFilter {
  action?: string;
  target?: string;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case)
// --------------------------------------------------------------------------- //
export interface ApiPaginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ApiAdminMe {
  id: string;
  user_id: string;
  role: AdminRole;
  full_name: string | null;
  permissions: string[];
  status: AdminStatus;
}

export interface ApiOverviewCard {
  key: string;
  value: number | null;
}

export interface ApiAdminDashboard {
  cards: ApiOverviewCard[];
  procurement_status_counts: Record<string, number>;
  generated_at: string;
}

export interface ApiFarmerRow {
  user_id: string;
  farmer_ref?: string;
  full_name: string | null;
  phone_number: string | null;
  district: string | null;
  village: string | null;
  primary_crop: string | null;
  language: string | null;
  farm_count: number;
  created_at: string | null;
}

export interface ApiFarmSummary {
  id: string;
  name: string;
  crop: string | null;
  area_hectares: number | null;
  status: string;
  created_at: string;
}

export interface ApiFarmerDetail {
  user_id: string;
  farmer_ref?: string;
  full_name: string | null;
  phone_number: string | null;
  district: string | null;
  block: string | null;
  village: string | null;
  primary_crop: string | null;
  language: string | null;
  farms: ApiFarmSummary[];
  counts: Record<string, number>;
}

export interface ApiAnalytics {
  farmer_growth: DistributionItem[];
  crop_distribution: DistributionItem[];
  disease_distribution: DistributionItem[];
  nutrient_deficiencies: DistributionItem[];
  soil_categories: DistributionItem[];
  expert_trends: DistributionItem[];
  produce_by_crop: DistributionItem[];
}

export interface ApiProcurementRow {
  offer_id: string;
  listing_ref?: string;
  farmer_ref?: string;
  crop: string | null;
  variety: string | null;
  quantity: number;
  unit: string;
  expected_grade: string | null;
  harvest_date: string | null;
  village: string | null;
  district: string | null;
  farmer_name: string | null;
  offer_status: string;
  admin_status: ProcurementStatus;
  assigned_admin_id: string | null;
  follow_up_at: string | null;
  buyer_name: string | null;
  buyer_contact: string | null;
  buyer_contact_masked: boolean;
  cultivated_area_hectares: number | null;
  expected_total_quantity: number | null;
  available_quantity: number | null;
  quantity_provenance: string | null;
  quality_notes: string | null;
  buyer_offer_quantity: number | null;
  buyer_offer_price: number | null;
  transport_cost: number | null;
  commission_rate: number | null;
  negotiation_notes: string | null;
}

export interface ApiProcurementBucket {
  label: string;
  count: number;
  quantity_kg: number;
}

export interface ApiQuantityTrendPoint {
  label: string;
  quantity_kg: number;
  count: number;
}

export interface ApiProcurementAnalytics {
  by_village: ApiProcurementBucket[];
  by_crop: ApiProcurementBucket[];
  by_season: ApiProcurementBucket[];
  quantity_trend: ApiQuantityTrendPoint[];
  total_offers: number;
  total_quantity_kg: number;
}

export interface ApiProcurementView {
  page: ApiPaginated<ApiProcurementRow>;
  analytics: ApiProcurementAnalytics;
}

export interface ApiAiMonitoring {
  today_requests: number | null;
  total_messages: number | null;
  disease_detections: number | null;
  nutrient_analyses: number | null;
  satellite_analyses: number | null;
  memory_generated: number | null;
  intelligence_reports: number | null;
  average_confidence: number | null;
  daily_requests: DailyPoint[];
  model_latency_ms: number | null;
  api_failures: number | null;
}

export interface ApiBroadcast {
  id: string;
  title: string;
  body: string;
  language: string;
  target_type: BroadcastTargetType;
  target_value: string | null;
  schedule_type: BroadcastScheduleType;
  status: BroadcastStatus;
  recipient_count: number;
  delivered_count: number;
  scheduled_for: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface ApiNotificationsOverview {
  broadcasts: ApiPaginated<ApiBroadcast>;
  delivered_total: number;
}

export interface ApiAuditRow {
  id: string;
  admin_id: string | null;
  role: string | null;
  action: string;
  target: string | null;
  target_id: string | null;
  ip_address: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}
