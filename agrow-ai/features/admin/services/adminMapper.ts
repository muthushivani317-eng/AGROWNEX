import type {
  AdminAnalytics,
  AdminDashboard,
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
  ApiProcurementAnalytics,
  ApiProcurementRow,
  ApiProcurementView,
  AuditRow,
  Broadcast,
  FarmerDetail,
  FarmerRow,
  NotificationsOverview,
  ProcurementAnalytics,
  ProcurementRow,
  ProcurementView,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). No I/O. */

export function apiToMe(dto: ApiAdminMe): AdminMe {
  return {
    id: dto.id,
    userId: dto.user_id,
    role: dto.role,
    fullName: dto.full_name,
    permissions: dto.permissions ?? [],
    status: dto.status,
    isSample: false,
  };
}

export function apiToDashboard(dto: ApiAdminDashboard): AdminDashboard {
  return {
    cards: (dto.cards ?? []).map((c) => ({ key: c.key, value: c.value })),
    procurementStatusCounts: dto.procurement_status_counts ?? {},
    generatedAt: dto.generated_at,
    isSample: false,
  };
}

export function apiToFarmerRow(dto: ApiFarmerRow): FarmerRow {
  return {
    userId: dto.user_id,
    farmerRef: dto.farmer_ref,
    fullName: dto.full_name,
    phoneNumber: dto.phone_number,
    district: dto.district,
    village: dto.village,
    primaryCrop: dto.primary_crop,
    language: dto.language,
    farmCount: dto.farm_count,
    createdAt: dto.created_at,
  };
}

export function apiToFarmerDetail(dto: ApiFarmerDetail): FarmerDetail {
  return {
    userId: dto.user_id,
    farmerRef: dto.farmer_ref,
    fullName: dto.full_name,
    phoneNumber: dto.phone_number,
    district: dto.district,
    block: dto.block,
    village: dto.village,
    primaryCrop: dto.primary_crop,
    language: dto.language,
    farms: (dto.farms ?? []).map((f) => ({
      id: f.id,
      name: f.name,
      crop: f.crop,
      areaHectares: f.area_hectares,
      status: f.status,
      createdAt: f.created_at,
    })),
    counts: dto.counts ?? {},
  };
}

export function apiToAnalytics(dto: ApiAnalytics): AdminAnalytics {
  return {
    farmerGrowth: dto.farmer_growth ?? [],
    cropDistribution: dto.crop_distribution ?? [],
    diseaseDistribution: dto.disease_distribution ?? [],
    nutrientDeficiencies: dto.nutrient_deficiencies ?? [],
    soilCategories: dto.soil_categories ?? [],
    expertTrends: dto.expert_trends ?? [],
    produceByCrop: dto.produce_by_crop ?? [],
    isSample: false,
  };
}

export function apiToProcurementRow(dto: ApiProcurementRow): ProcurementRow {
  return {
    offerId: dto.offer_id,
    listingRef: dto.listing_ref,
    farmerRef: dto.farmer_ref,
    crop: dto.crop,
    variety: dto.variety,
    quantity: dto.quantity,
    unit: dto.unit,
    expectedGrade: dto.expected_grade,
    harvestDate: dto.harvest_date,
    village: dto.village,
    district: dto.district,
    farmerName: dto.farmer_name,
    offerStatus: dto.offer_status,
    adminStatus: dto.admin_status,
    assignedAdminId: dto.assigned_admin_id,
    followUpAt: dto.follow_up_at,
    buyerName: dto.buyer_name,
    buyerContact: dto.buyer_contact,
    buyerContactMasked: dto.buyer_contact_masked,
    cultivatedAreaHectares: dto.cultivated_area_hectares,
    expectedTotalQuantity: dto.expected_total_quantity,
    availableQuantity: dto.available_quantity,
    quantityProvenance: dto.quantity_provenance,
    qualityNotes: dto.quality_notes,
    buyerOfferQuantity: dto.buyer_offer_quantity,
    buyerOfferPrice: dto.buyer_offer_price,
    transportCost: dto.transport_cost,
    commissionRate: dto.commission_rate,
    negotiationNotes: dto.negotiation_notes,
  };
}

export function apiToProcurementAnalytics(dto: ApiProcurementAnalytics): ProcurementAnalytics {
  const bucket = (b: { label: string; count: number; quantity_kg: number }) => ({
    label: b.label,
    count: b.count,
    quantityKg: b.quantity_kg,
  });
  return {
    byVillage: (dto.by_village ?? []).map(bucket),
    byCrop: (dto.by_crop ?? []).map(bucket),
    bySeason: (dto.by_season ?? []).map(bucket),
    quantityTrend: (dto.quantity_trend ?? []).map((p) => ({
      label: p.label,
      quantityKg: p.quantity_kg,
      count: p.count,
    })),
    totalOffers: dto.total_offers,
    totalQuantityKg: dto.total_quantity_kg,
  };
}

export function apiToProcurementView(dto: ApiProcurementView): ProcurementView {
  return {
    page: {
      items: (dto.page.items ?? []).map(apiToProcurementRow),
      page: dto.page.page,
      pageSize: dto.page.page_size,
      total: dto.page.total,
      totalPages: dto.page.total_pages,
    },
    analytics: apiToProcurementAnalytics(dto.analytics),
    isSample: false,
  };
}

export function apiToAiMonitoring(dto: ApiAiMonitoring): AiMonitoring {
  return {
    todayRequests: dto.today_requests,
    totalMessages: dto.total_messages,
    diseaseDetections: dto.disease_detections,
    nutrientAnalyses: dto.nutrient_analyses,
    satelliteAnalyses: dto.satellite_analyses,
    memoryGenerated: dto.memory_generated,
    intelligenceReports: dto.intelligence_reports,
    averageConfidence: dto.average_confidence,
    dailyRequests: dto.daily_requests ?? [],
    modelLatencyMs: dto.model_latency_ms,
    apiFailures: dto.api_failures,
    isSample: false,
  };
}

export function apiToBroadcast(dto: ApiBroadcast): Broadcast {
  return {
    id: dto.id,
    title: dto.title,
    body: dto.body,
    language: dto.language,
    targetType: dto.target_type,
    targetValue: dto.target_value,
    scheduleType: dto.schedule_type,
    status: dto.status,
    recipientCount: dto.recipient_count,
    deliveredCount: dto.delivered_count,
    scheduledFor: dto.scheduled_for,
    sentAt: dto.sent_at,
    createdAt: dto.created_at,
    isSample: false,
  };
}

export function apiToNotificationsOverview(
  dto: ApiNotificationsOverview,
): NotificationsOverview {
  return {
    broadcasts: {
      items: (dto.broadcasts.items ?? []).map(apiToBroadcast),
      page: dto.broadcasts.page,
      pageSize: dto.broadcasts.page_size,
      total: dto.broadcasts.total,
      totalPages: dto.broadcasts.total_pages,
    },
    deliveredTotal: dto.delivered_total,
    isSample: false,
  };
}

export function apiToAuditRow(dto: ApiAuditRow): AuditRow {
  return {
    id: dto.id,
    adminId: dto.admin_id,
    role: dto.role,
    action: dto.action,
    target: dto.target,
    targetId: dto.target_id,
    ipAddress: dto.ip_address,
    meta: dto.meta,
    createdAt: dto.created_at,
  };
}
