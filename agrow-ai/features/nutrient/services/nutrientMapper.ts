import type { SupportedLanguage } from "@/types";

import type {
  ApiNutrientAnalysis,
  ApiNutrientHistoryEntry,
  ApiNutrientRecommendation,
  ApiNutrientReport,
  NutrientAnalysis,
  NutrientHistoryEntry,
  NutrientRecommendation,
  NutrientReport,
} from "../types";

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

const toLang = (v: string): SupportedLanguage => (v === "en" ? "en" : "ta");

export function apiToRecommendation(
  dto: ApiNutrientRecommendation,
): NutrientRecommendation {
  return {
    category: dto.category,
    code: dto.code,
    nutrient: dto.nutrient,
    severity: dto.severity,
    priority: dto.priority,
  };
}

export function apiToAnalysis(dto: ApiNutrientAnalysis): NutrientAnalysis {
  return {
    primaryDeficiency: dto.primary_deficiency,
    secondaryDeficiency: dto.secondary_deficiency,
    status: dto.status,
    confidence: dto.confidence,
    severity: dto.severity,
    affectedArea: dto.affected_area,
    diseaseConflict: dto.disease_conflict,
    needsTest: dto.needs_test,
    needsExpert: dto.needs_expert,
    soilReference: dto.soil_reference,
    satelliteReference: dto.satellite_reference,
    weatherReference: dto.weather_reference,
    explanationTamil: dto.explanation_tamil,
    explanationEnglish: dto.explanation_english,
    resultCode: dto.result_code ?? "abstained",
    confidenceBand: dto.confidence_band ?? "low",
    evidenceObserved: dto.evidence_observed ?? [],
    evidenceMissing: dto.evidence_missing ?? ["compatible_corroboration"],
    conflicts: dto.conflicts ?? [],
    abstentionReason: dto.abstention_reason ?? "legacy_result_unverified",
    suggestedNextEvidence: dto.suggested_next_evidence ?? ["expert_review"],
    expertVerified: dto.expert_verified === true,
  };
}

export function apiToReport(dto: ApiNutrientReport): NutrientReport {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    crop: dto.crop,
    imageUrl: dto.image_url,
    thumbnailUrl: dto.thumbnail_url,
    captureDate: dto.capture_date,
    provider: dto.provider,
    modelUsed: dto.model_used,
    status: dto.status,
    language: toLang(dto.language),
    latitude: dto.latitude,
    longitude: dto.longitude,
    weatherSnapshot: dto.weather_snapshot,
    analysis: dto.analysis ? apiToAnalysis(dto.analysis) : null,
    symptoms: dto.symptoms ?? [],
    recommendations: (dto.recommendations ?? []).map(apiToRecommendation),
    createdAt: dto.created_at,
  };
}

export function apiToHistoryEntry(
  dto: ApiNutrientHistoryEntry,
): NutrientHistoryEntry {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    reportId: dto.report_id,
    crop: dto.crop,
    primaryDeficiency: dto.primary_deficiency,
    status: dto.status,
    confidence: dto.confidence,
    severity: dto.severity,
    recordedAt: dto.recorded_at,
  };
}
