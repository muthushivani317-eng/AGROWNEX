import type {
  ApiSoilAssessment,
  ApiSoilDashboard,
  ApiSoilHistoryEntry,
  ApiSoilProfile,
  ApiSoilRecommendation,
  ApiSoilReport,
  ApiSoilTestResult,
  SoilAssessment,
  SoilDashboard,
  SoilHistoryEntry,
  SoilProfile,
  SoilRecommendation,
  SoilReport,
  SoilReportInput,
  SoilTestResult,
} from "../types";

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToResult(
  dto: ApiSoilTestResult | null,
): SoilTestResult | null {
  if (!dto) return null;
  return {
    ph: dto.ph,
    organicCarbon: dto.organic_carbon,
    nitrogen: dto.nitrogen,
    phosphorus: dto.phosphorus,
    potassium: dto.potassium,
    sulphur: dto.sulphur,
    ecSalinity: dto.ec_salinity,
    waterHoldingCapacity: dto.water_holding_capacity,
    drainage: dto.drainage,
    micronutrients: dto.micronutrients,
  };
}

export function apiToReport(dto: ApiSoilReport): SoilReport {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    source: dto.source,
    reportUrl: dto.report_url,
    thumbnailUrl: dto.thumbnail_url,
    labName: dto.lab_name,
    testDate: dto.test_date,
    notes: dto.notes,
    status: dto.status,
    confidence: dto.confidence,
    createdAt: dto.created_at,
    result: apiToResult(dto.result),
  };
}

export function apiToProfile(dto: ApiSoilProfile): SoilProfile {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    soilType: dto.soil_type,
    latitude: dto.latitude,
    longitude: dto.longitude,
    ph: dto.ph,
    organicCarbon: dto.organic_carbon,
    nitrogen: dto.nitrogen,
    phosphorus: dto.phosphorus,
    potassium: dto.potassium,
    micronutrients: dto.micronutrients,
    ecSalinity: dto.ec_salinity,
    waterHoldingCapacity: dto.water_holding_capacity,
    drainage: dto.drainage,
    source: dto.source,
    confidence: dto.confidence,
    lastTestDate: dto.last_test_date,
    updatedAt: dto.updated_at,
  };
}

export function apiToAssessment(
  dto: ApiSoilAssessment | null,
): SoilAssessment | null {
  if (!dto) return null;
  return {
    phClass: dto.ph_class,
    organicCarbon: dto.organic_carbon,
    nitrogen: dto.nitrogen,
    phosphorus: dto.phosphorus,
    potassium: dto.potassium,
    salinity: dto.salinity,
    deficientMicronutrients: dto.deficient_micronutrients ?? [],
    hasAnyValue: dto.has_any_value,
  };
}

export function apiToRecommendation(
  dto: ApiSoilRecommendation,
): SoilRecommendation {
  return {
    category: dto.category,
    code: dto.code,
    parameter: dto.parameter,
    rating: dto.rating,
    severity: dto.severity,
    priority: dto.priority,
    value: dto.value,
    unit: dto.unit,
  };
}

export function apiToHistoryEntry(dto: ApiSoilHistoryEntry): SoilHistoryEntry {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    reportId: dto.report_id,
    testDate: dto.test_date,
    ph: dto.ph,
    organicCarbon: dto.organic_carbon,
    nitrogen: dto.nitrogen,
    phosphorus: dto.phosphorus,
    potassium: dto.potassium,
    source: dto.source,
    confidence: dto.confidence,
    recordedAt: dto.recorded_at,
  };
}

export function apiToDashboard(dto: ApiSoilDashboard): SoilDashboard {
  return {
    farmId: dto.farm_id,
    hasData: dto.has_data,
    messageCode: dto.message_code,
    profile: dto.profile ? apiToProfile(dto.profile) : null,
    assessment: apiToAssessment(dto.assessment),
    recommendations: (dto.recommendations ?? []).map(apiToRecommendation),
    latestReport: dto.latest_report ? apiToReport(dto.latest_report) : null,
    indicatorEvidence: (dto.indicator_evidence ?? []).map((item) => ({
      indicator: item.indicator,
      value: item.value,
      unit: item.unit,
      evidenceType: item.evidence_type,
      collectionMethod: item.collection_method,
      collectedAt: item.collected_at,
      sourceReference: item.source_reference,
      spatialCoverage: item.spatial_coverage,
      confidence: item.confidence,
      uncertaintyLow: item.uncertainty_low,
      uncertaintyHigh: item.uncertainty_high,
      verificationState: item.verification_state,
      freshness: item.freshness,
      status: item.status,
      reportReference: item.report_reference,
    })),
    overallStatus: dto.overall_status ?? "insufficient_data",
    laboratoryEquivalent: false,
  };
}

/** Domain input → backend request body (camelCase → snake_case). */
export function reportInputToApi(
  input: SoilReportInput,
): Record<string, unknown> {
  const v = input.values;
  return {
    farm_id: input.farmId,
    source: input.source ?? "self",
    report_url: input.reportUrl ?? null,
    thumbnail_url: input.thumbnailUrl ?? null,
    mime_type: input.mimeType ?? null,
    lab_name: input.labName ?? null,
    test_date: input.testDate ?? null,
    notes: input.notes ?? null,
    values: {
      ph: v.ph ?? null,
      organic_carbon: v.organicCarbon ?? null,
      nitrogen: v.nitrogen ?? null,
      phosphorus: v.phosphorus ?? null,
      potassium: v.potassium ?? null,
      sulphur: v.sulphur ?? null,
      ec_salinity: v.ecSalinity ?? null,
      water_holding_capacity: v.waterHoldingCapacity ?? null,
      drainage: v.drainage ?? null,
      micronutrients: v.micronutrients ?? null,
    },
  };
}
