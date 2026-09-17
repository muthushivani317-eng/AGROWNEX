import { appStorage } from '@/lib/storage';

import type {
  AdminAnalytics,
  AdminDashboard,
  AdminMe,
  AiMonitoring,
  AuditFilter,
  AuditRow,
  Broadcast,
  BroadcastInput,
  CropIntelligence,
  CropIntelligenceFilter,
  FarmerDetail,
  FarmerFilter,
  FarmerRow,
  NotificationsOverview,
  Paginated,
  ProcurementFilter,
  ProcurementRow,
  ProcurementStatus,
  ProcurementView,
} from '../types';
import { AdminError, type AdminProvider } from './adminProvider';
import {
  SAMPLE_ADMIN,
  SAMPLE_AI,
  SAMPLE_AUDIT,
  SAMPLE_BROADCASTS,
  SAMPLE_FARMER_DETAILS,
  SAMPLE_FARMERS,
  SAMPLE_OFFERS,
  SAMPLE_OVERVIEW,
  type SampleOffer,
} from './adminSamples';
import { computeProcurementAnalytics } from './procurementAnalytics';

/**
 * Local admin provider — serves the deterministic sample dataset (flagged `isSample`)
 * so the team dashboard is fully explorable without a backend. Procurement status
 * changes and broadcasts are persisted to MMKV and audited locally, mirroring the
 * server's immutable-trail behaviour. Never presents sample data as real.
 */
const STATUS_KEY = 'agrowai.admin.procurementStatus';
const BROADCAST_KEY = 'agrowai.admin.broadcasts';
const AUDIT_KEY = 'agrowai.admin.audit';

function statusOverrides(): Record<string, ProcurementStatus> {
  return appStorage.getJSON<Record<string, ProcurementStatus>>(STATUS_KEY) ?? {};
}

function localBroadcasts(): Broadcast[] {
  return appStorage.getJSON<Broadcast[]>(BROADCAST_KEY) ?? [];
}

function localAudit(): AuditRow[] {
  return appStorage.getJSON<AuditRow[]>(AUDIT_KEY) ?? [];
}

function appendAudit(entry: AuditRow): void {
  appStorage.setJSON(AUDIT_KEY, [entry, ...localAudit()]);
}

function paginate<T>(items: T[], page: number, pageSize: number): Paginated<T> {
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    page,
    pageSize,
    total: items.length,
    totalPages: items.length ? Math.ceil(items.length / pageSize) : 0,
  };
}

function offerToRow(offer: SampleOffer): ProcurementRow {
  const override = statusOverrides()[offer.offerId];
  return {
    offerId: offer.offerId,
    crop: offer.crop,
    variety: offer.variety,
    quantity: offer.quantity,
    unit: offer.unit,
    expectedGrade: offer.expectedGrade,
    harvestDate: offer.harvestDate,
    village: offer.village,
    district: offer.district,
    farmerName: offer.farmerName,
    offerStatus: offer.offerStatus,
    adminStatus: override ?? 'new',
    assignedAdminId: null,
    followUpAt: null,
    buyerName: null,
    buyerContact: null,
    buyerContactMasked: false,
    cultivatedAreaHectares: null,
    expectedTotalQuantity: offer.quantity,
    availableQuantity: offer.quantity,
    quantityProvenance: 'farmer_reported',
    qualityNotes: null,
    buyerOfferQuantity: null,
    buyerOfferPrice: null,
    transportCost: null,
    commissionRate: null,
    negotiationNotes: null,
  };
}

function countBy(items: (string | null)[]): { label: string; count: number }[] {
  const map = new Map<string, number>();
  for (const item of items) {
    const key = item ?? 'unknown';
    map.set(key, (map.get(key) ?? 0) + 1);
  }
  return [...map.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count);
}

export const localAdminProvider: AdminProvider = {
  async me(): Promise<AdminMe> {
    return SAMPLE_ADMIN;
  },

  async dashboard(): Promise<AdminDashboard> {
    const overrides = statusOverrides();
    const counts: Record<string, number> = {};
    for (const offer of SAMPLE_OFFERS) {
      const status = overrides[offer.offerId] ?? 'new';
      counts[status] = (counts[status] ?? 0) + 1;
    }
    return {
      cards: SAMPLE_OVERVIEW,
      procurementStatusCounts: counts,
      generatedAt: new Date().toISOString(),
      isSample: true,
    };
  },

  async businessDashboard() {
    return {
      generated_at: new Date().toISOString(), total_farmers: SAMPLE_FARMERS.length,
      new_farmers_today: 0, active_farmers_today: 0, active_farmers_7d: 0,
      active_farmers_30d: 0, produce_listings_today: 0,
      procurement_status_counts: {}, transactions: 0, gmv: '0',
      buyer_receipts: '0', payment_outstanding: '0', earned_commission: '0', currency: 'INR',
    };
  },

  async farmers(
    filter?: FarmerFilter,
    page = 1,
    pageSize = 20,
  ): Promise<Paginated<FarmerRow>> {
    let rows = [...SAMPLE_FARMERS];
    if (filter?.district) rows = rows.filter((r) => r.district === filter.district);
    if (filter?.crop) rows = rows.filter((r) => r.primaryCrop === filter.crop);
    if (filter?.search) {
      const q = filter.search.toLowerCase();
      rows = rows.filter(
        (r) =>
          (r.fullName ?? '').toLowerCase().includes(q) ||
          (r.village ?? '').toLowerCase().includes(q) ||
          (r.phoneNumber ?? '').includes(filter.search as string),
      );
    }
    return paginate(rows, page, pageSize);
  },

  async farmerDetail(userId: string): Promise<FarmerDetail> {
    const detail = SAMPLE_FARMER_DETAILS[userId];
    if (!detail) throw new AdminError('not_found', 'Farmer not found');
    return detail;
  },

  async analytics(): Promise<AdminAnalytics> {
    return {
      farmerGrowth: [
        { label: '2026-02', count: 180 },
        { label: '2026-03', count: 232 },
        { label: '2026-04', count: 271 },
        { label: '2026-05', count: 300 },
        { label: '2026-06', count: 341 },
        { label: '2026-07', count: 372 },
      ],
      cropDistribution: countBy(SAMPLE_FARMERS.map((f) => f.primaryCrop)),
      diseaseDistribution: [
        { label: 'Leaf blast', count: 61 },
        { label: 'Brown spot', count: 43 },
        { label: 'Sheath blight', count: 22 },
      ],
      nutrientDeficiencies: [
        { label: 'nitrogen', count: 38 },
        { label: 'zinc', count: 21 },
        { label: 'potassium', count: 12 },
      ],
      soilCategories: [
        { label: 'clay', count: 96 },
        { label: 'loam', count: 54 },
        { label: 'sandy', count: 31 },
      ],
      expertTrends: [
        { label: 'resolved', count: 40 },
        { label: 'awaiting_expert', count: 14 },
        { label: 'assigned', count: 10 },
      ],
      produceByCrop: countBy(SAMPLE_OFFERS.map((o) => o.crop)),
      isSample: true,
    };
  },

  async cropIntelligence(filter?: CropIntelligenceFilter): Promise<CropIntelligence> {
    const crop = filter?.crop?.toLowerCase();
    const district = filter?.district?.toLowerCase();
    const village = filter?.village?.toLowerCase();
    const farmers = SAMPLE_FARMERS.filter((farmer) =>
      (!crop || farmer.primaryCrop?.toLowerCase() === crop) &&
      (!district || farmer.district?.toLowerCase() === district) &&
      (!village || farmer.village?.toLowerCase() === village));
    const offers = SAMPLE_OFFERS.filter((offer) =>
      (!crop || offer.crop?.toLowerCase() === crop) &&
      (!district || offer.district?.toLowerCase() === district) &&
      (!village || offer.village?.toLowerCase() === village));
    const days = filter?.harvestDays ?? 30;
    const start = new Date();
    const end = new Date(start.getTime() + days * 86400000);
    const upcoming = offers.filter((offer) => {
      const date = new Date(offer.harvestDate ?? '');
      return date >= start && date <= end;
    });
    return {
      generatedAt: new Date().toISOString(), filters: { ...filter, harvestDays: days },
      summary: { farmerCount: farmers.length, farmCount: farmers.reduce((n, f) => n + f.farmCount, 0),
        knownAreaHectares: 0, farmsWithArea: 0,
        farmsWithoutArea: farmers.reduce((n, f) => n + f.farmCount, 0), recordedStageFarms: 0,
        saleListingCount: offers.length, harvestWindowFarmerCount: upcoming.length,
        harvestWindowListingCount: upcoming.length },
      byCrop: countBy(farmers.map((f) => f.primaryCrop)).map((item) => ({ ...item, farmCount: item.count,
        farmerCount: item.count, knownAreaHectares: 0, farmsWithArea: 0 })),
      byLocation: countBy(farmers.map((f) => [f.district, f.village].filter(Boolean).join(' / '))).map((item) => ({
        ...item, farmCount: item.count, farmerCount: item.count, knownAreaHectares: 0, farmsWithArea: 0 })),
      cropStages: [],
      offeredQuantities: offers.map((offer) => ({ unit: offer.unit, quantity: offer.quantity })),
      harvestWindow: { fromDate: start.toISOString().slice(0, 10), toDate: end.toISOString().slice(0, 10),
        farmerCount: upcoming.length, listingCount: upcoming.length }, isSample: true,
    };
  },

  async procurement(
    filter?: ProcurementFilter,
    page = 1,
    pageSize = 20,
  ): Promise<ProcurementView> {
    let offers = [...SAMPLE_OFFERS];
    if (filter?.crop) offers = offers.filter((o) => o.crop === filter.crop);
    if (filter?.village) offers = offers.filter((o) => o.village === filter.village);
    if (filter?.district) offers = offers.filter((o) => o.district === filter.district);

    const rows = offers.map(offerToRow);
    const analytics = computeProcurementAnalytics(
      offers.map((o) => ({
        village: o.village,
        crop: o.crop,
        harvestDate: o.harvestDate,
        quantity: o.quantity,
        unit: o.unit,
      })),
    );
    return { page: paginate(rows, page, pageSize), analytics, isSample: true };
  },

  async updateProcurementStatus(
    offerId: string,
    status: ProcurementStatus,
  ): Promise<ProcurementStatus> {
    if (!SAMPLE_OFFERS.some((o) => o.offerId === offerId)) {
      throw new AdminError('not_found', 'Produce offer not found');
    }
    const overrides = statusOverrides();
    const previous = overrides[offerId] ?? 'new';
    overrides[offerId] = status;
    appStorage.setJSON(STATUS_KEY, overrides);
    appendAudit({
      id: `local-${Date.now()}`,
      adminId: SAMPLE_ADMIN.id,
      role: SAMPLE_ADMIN.role,
      action: 'procurement_status_changed',
      target: 'procurement',
      targetId: offerId,
      ipAddress: 'local',
      meta: { status, previous },
      createdAt: new Date().toISOString(),
    });
    return status;
  },

  async updateProcurementCase(offerId, input) {
    if (input.status) await this.updateProcurementStatus(offerId, input.status);
    const offer = SAMPLE_OFFERS.find((item) => item.offerId === offerId);
    if (!offer) throw new AdminError('not_found', 'Produce offer not found');
    return {
      ...offerToRow(offer),
      assignedAdminId: input.assignedAdminId ?? null,
      followUpAt: input.followUpAt ?? null,
      buyerName: input.buyerName ?? null,
      buyerContact: null,
      buyerContactMasked: Boolean(input.buyerContact),
      buyerOfferQuantity: input.buyerOfferQuantity ?? null,
      buyerOfferPrice: input.buyerOfferPrice ?? null,
      transportCost: input.transportCost ?? null,
      commissionRate: input.commissionRate ?? null,
      negotiationNotes: input.negotiationNotes ?? null,
    };
  },

  async revealBuyerContact() {
    return '+919000000000';
  },

  async commerceLedger(offerId) {
    return { offer_id: offerId, case_status: 'new', transaction: null, pickups: [], payments: [], commissions: [] };
  },
  async recordPickup() {},
  async recordTransaction() { return { id: `local-transaction-${Date.now()}` }; },
  async recordPayment() {},
  async recordCommission() {},

  async ai(): Promise<AiMonitoring> {
    return SAMPLE_AI;
  },

  async notifications(page = 1, pageSize = 20): Promise<NotificationsOverview> {
    const all = [...localBroadcasts(), ...SAMPLE_BROADCASTS];
    const deliveredTotal = all.reduce((sum, b) => sum + b.deliveredCount, 0);
    return { broadcasts: paginate(all, page, pageSize), deliveredTotal, isSample: true };
  },

  async sendBroadcast(input: BroadcastInput): Promise<Broadcast> {
    const matches = (f: FarmerRow): boolean => {
      switch (input.targetType) {
        case 'village':
          return f.village === input.targetValue;
        case 'district':
          return f.district === input.targetValue;
        case 'crop':
          return f.primaryCrop === input.targetValue;
        case 'language':
          return f.language === input.targetValue;
        default:
          return true;
      }
    };
    const recipientCount = SAMPLE_FARMERS.filter(matches).length;
    const immediate = input.scheduleType === 'immediate';
    const now = new Date().toISOString();
    const broadcast: Broadcast = {
      id: `local-bc-${Date.now()}`,
      title: input.title,
      body: input.body,
      language: input.language,
      targetType: input.targetType,
      targetValue: input.targetValue ?? null,
      scheduleType: input.scheduleType,
      status: immediate ? 'sent' : 'queued',
      recipientCount,
      deliveredCount: immediate ? recipientCount : 0,
      scheduledFor: input.scheduledFor ?? null,
      sentAt: immediate ? now : null,
      createdAt: now,
      isSample: true,
    };
    appStorage.setJSON(BROADCAST_KEY, [broadcast, ...localBroadcasts()]);
    appendAudit({
      id: `local-${Date.now()}`,
      adminId: SAMPLE_ADMIN.id,
      role: SAMPLE_ADMIN.role,
      action: 'broadcast_sent',
      target: 'broadcast',
      targetId: broadcast.id,
      ipAddress: 'local',
      meta: { target_type: input.targetType, recipients: recipientCount, immediate },
      createdAt: now,
    });
    return broadcast;
  },

  async audit(
    filter?: AuditFilter,
    page = 1,
    pageSize = 20,
  ): Promise<Paginated<AuditRow>> {
    let rows = [...localAudit(), ...SAMPLE_AUDIT];
    if (filter?.action) rows = rows.filter((r) => r.action === filter.action);
    if (filter?.target) rows = rows.filter((r) => r.target === filter.target);
    return paginate(rows, page, pageSize);
  },
};
