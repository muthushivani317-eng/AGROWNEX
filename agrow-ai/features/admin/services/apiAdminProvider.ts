import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError } from '@/types';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  AdminAnalytics,
  AdminDashboard,
  BusinessDashboard,
  CommerceLedger,
  CropIntelligence,
  CropIntelligenceFilter,
  AdminMe,
  AiMonitoring,
  ApiAdminDashboard,
  ApiAdminMe,
  ApiAiMonitoring,
  ApiAnalytics,
  ApiAuditRow,
  ApiBroadcast,
  ApiFarmerDetail,
  ApiFarmerRow,
  ApiNotificationsOverview,
  ApiPaginated,
  ApiProcurementView,
  ApiProcurementRow,
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
import {
  apiToAiMonitoring,
  apiToAnalytics,
  apiToAuditRow,
  apiToBroadcast,
  apiToDashboard,
  apiToFarmerDetail,
  apiToFarmerRow,
  apiToMe,
  apiToNotificationsOverview,
  apiToProcurementView,
  apiToProcurementRow,
} from './adminMapper';
import { AdminError, type AdminProvider } from './adminProvider';

/**
 * Backend admin provider (docs/API_CONTRACT → ADMIN). RBAC, auditing and aggregation
 * run server-side; this layer only maps the response envelope. A `not_an_admin` /
 * `permission_denied` error is normalised so screens can render an access-denied state.
 */
function guard(err: unknown): never {
  if (err instanceof ApiError) {
    if (err.errorCode === 'not_an_admin' || err.errorCode === 'admin_suspended') {
      throw new AdminError('forbidden', err.message);
    }
    if (err.errorCode === 'permission_denied') {
      throw new AdminError('permission_denied', err.message);
    }
  }
  throw err;
}

function farmerParams(filter?: FarmerFilter): Record<string, string> {
  const p: Record<string, string> = {};
  if (filter?.search) p.search = filter.search;
  if (filter?.district) p.district = filter.district;
  if (filter?.crop) p.crop = filter.crop;
  return p;
}

export const apiAdminProvider: AdminProvider = {
  async me(): Promise<AdminMe> {
    try {
      return apiToMe(await api.get<ApiAdminMe>(endpoints.admin.me));
    } catch (err) {
      return guard(err);
    }
  },

  async dashboard(): Promise<AdminDashboard> {
    try {
      return apiToDashboard(await api.get<ApiAdminDashboard>(endpoints.admin.dashboard));
    } catch (err) {
      return guard(err);
    }
  },

  async businessDashboard(): Promise<BusinessDashboard> {
    try { return await api.get<BusinessDashboard>(endpoints.admin.businessDashboard); }
    catch (err) { return guard(err); }
  },

  async farmers(
    filter?: FarmerFilter,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<FarmerRow>> {
    try {
      const dto = await api.get<ApiPaginated<ApiFarmerRow>>(endpoints.admin.farmers, {
        params: { page, page_size: pageSize, ...farmerParams(filter) },
      });
      return {
        items: dto.items.map(apiToFarmerRow),
        page: dto.page,
        pageSize: dto.page_size,
        total: dto.total,
        totalPages: dto.total_pages,
      };
    } catch (err) {
      return guard(err);
    }
  },

  async farmerDetail(userId: string): Promise<FarmerDetail> {
    try {
      return apiToFarmerDetail(
        await api.get<ApiFarmerDetail>(endpoints.admin.farmer(userId)),
      );
    } catch (err) {
      return guard(err);
    }
  },

  async analytics(): Promise<AdminAnalytics> {
    try {
      return apiToAnalytics(await api.get<ApiAnalytics>(endpoints.admin.analytics));
    } catch (err) {
      return guard(err);
    }
  },

  async cropIntelligence(filter?: CropIntelligenceFilter): Promise<CropIntelligence> {
    try {
      const params: Record<string, string | number> = {};
      if (filter?.crop) params.crop = filter.crop;
      if (filter?.district) params.district = filter.district;
      if (filter?.village) params.village = filter.village;
      params.harvest_days = filter?.harvestDays ?? 30;
      const dto = await api.get<any>(endpoints.admin.cropIntelligence, { params });
      const group = (item: any) => ({
        label: item.label,
        farmCount: item.farm_count,
        farmerCount: item.farmer_count,
        knownAreaHectares: item.known_area_hectares,
        farmsWithArea: item.farms_with_area,
      });
      return {
        generatedAt: dto.generated_at,
        filters: {
          crop: dto.filters.crop ?? undefined,
          district: dto.filters.district ?? undefined,
          village: dto.filters.village ?? undefined,
          harvestDays: dto.filters.harvest_days,
        },
        summary: {
          farmerCount: dto.summary.farmer_count,
          farmCount: dto.summary.farm_count,
          knownAreaHectares: dto.summary.known_area_hectares,
          farmsWithArea: dto.summary.farms_with_area,
          farmsWithoutArea: dto.summary.farms_without_area,
          recordedStageFarms: dto.summary.recorded_stage_farms,
          saleListingCount: dto.summary.sale_listing_count,
          harvestWindowFarmerCount: dto.summary.harvest_window_farmer_count,
          harvestWindowListingCount: dto.summary.harvest_window_listing_count,
        },
        byCrop: dto.by_crop.map(group),
        byLocation: dto.by_location.map(group),
        cropStages: dto.crop_stages.map((item: any) => ({ label: item.label, farmCount: item.farm_count })),
        offeredQuantities: dto.offered_quantities,
        harvestWindow: {
          fromDate: dto.harvest_window.from_date,
          toDate: dto.harvest_window.to_date,
          farmerCount: dto.harvest_window.farmer_count,
          listingCount: dto.harvest_window.listing_count,
        },
      };
    } catch (err) {
      return guard(err);
    }
  },

  async procurement(
    filter?: ProcurementFilter,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<ProcurementView> {
    try {
      const params: Record<string, string | number> = { page, page_size: pageSize };
      if (filter?.crop) params.crop = filter.crop;
      if (filter?.village) params.village = filter.village;
      if (filter?.district) params.district = filter.district;
      if (filter?.search) params.search = filter.search;
      return apiToProcurementView(
        await api.get<ApiProcurementView>(endpoints.admin.procurement, { params }),
      );
    } catch (err) {
      return guard(err);
    }
  },

  async updateProcurementStatus(
    offerId: string,
    status: ProcurementStatus,
    note?: string,
  ): Promise<ProcurementStatus> {
    try {
      const dto = await api.put<{ offer_id: string; status: ProcurementStatus }>(
        endpoints.admin.procurementStatus(offerId),
        { status, note: note ?? null },
      );
      return dto.status;
    } catch (err) {
      return guard(err);
    }
  },

  async updateProcurementCase(
    offerId: string,
    input: ProcurementCaseInput,
  ): Promise<ProcurementRow> {
    try {
      const dto = await api.put<ApiProcurementRow>(endpoints.admin.procurementCase(offerId), {
        status: input.status,
        assigned_admin_id: input.assignedAdminId,
        follow_up_at: input.followUpAt,
        buyer_name: input.buyerName,
        buyer_contact: input.buyerContact,
        buyer_offer_quantity: input.buyerOfferQuantity,
        buyer_offer_price: input.buyerOfferPrice,
        transport_cost: input.transportCost,
        commission_rate: input.commissionRate,
        currency: input.currency,
        price_unit: input.priceUnit,
        negotiation_notes: input.negotiationNotes,
      });
      return apiToProcurementRow(dto);
    } catch (err) {
      return guard(err);
    }
  },

  async revealBuyerContact(offerId: string): Promise<string> {
    try {
      const dto = await api.post<{ offer_id: string; buyer_contact: string }>(
        endpoints.admin.procurementBuyerContact(offerId),
        {},
      );
      return dto.buyer_contact;
    } catch (err) {
      return guard(err);
    }
  },

  async commerceLedger(offerId: string): Promise<CommerceLedger> {
    try { return await api.get<CommerceLedger>(endpoints.admin.procurementLedger(offerId)); }
    catch (err) { return guard(err); }
  },

  async recordPickup(offerId, input): Promise<void> {
    try { await api.post(endpoints.admin.procurementPickup(offerId), input); }
    catch (err) { return guard(err); }
  },

  async recordTransaction(offerId, occurredAt): Promise<{ id: string }> {
    try { return await api.post<{ id: string }>(endpoints.admin.procurementTransaction(offerId), { occurred_at: occurredAt }); }
    catch (err) { return guard(err); }
  },

  async recordPayment(transactionId, input): Promise<void> {
    try { await api.post(endpoints.admin.procurementPayment(transactionId), input); }
    catch (err) { return guard(err); }
  },

  async recordCommission(transactionId, occurredAt): Promise<void> {
    try { await api.post(endpoints.admin.procurementCommission(transactionId), { entry_type: 'earned', occurred_at: occurredAt }); }
    catch (err) { return guard(err); }
  },

  async ai(): Promise<AiMonitoring> {
    try {
      return apiToAiMonitoring(await api.get<ApiAiMonitoring>(endpoints.admin.ai));
    } catch (err) {
      return guard(err);
    }
  },

  async notifications(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<NotificationsOverview> {
    try {
      return apiToNotificationsOverview(
        await api.get<ApiNotificationsOverview>(endpoints.admin.notifications, {
          params: { page, page_size: pageSize },
        }),
      );
    } catch (err) {
      return guard(err);
    }
  },

  async sendBroadcast(input: BroadcastInput): Promise<Broadcast> {
    try {
      const dto = await api.post<ApiBroadcast>(endpoints.admin.broadcast, {
        title: input.title,
        body: input.body,
        language: input.language,
        target_type: input.targetType,
        target_value: input.targetValue ?? null,
        schedule_type: input.scheduleType,
        scheduled_for: input.scheduledFor ?? null,
      });
      return apiToBroadcast(dto);
    } catch (err) {
      return guard(err);
    }
  },

  async audit(
    filter?: AuditFilter,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<AuditRow>> {
    try {
      const params: Record<string, string | number> = { page, page_size: pageSize };
      if (filter?.action) params.action = filter.action;
      if (filter?.target) params.target = filter.target;
      const dto = await api.get<ApiPaginated<ApiAuditRow>>(endpoints.admin.audit, { params });
      return {
        items: dto.items.map(apiToAuditRow),
        page: dto.page,
        pageSize: dto.page_size,
        total: dto.total,
        totalPages: dto.total_pages,
      };
    } catch (err) {
      return guard(err);
    }
  },
};
