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
    confidenceBand: dto.confidence_band === undefined ? "low" : dto.confidence_band,
    evidenceObserved: dto.evidence_observed ?? [],
    evidenceMissing: dto.evidence_missing ?? ["compatible_corroboration"],
    conflicts: dto.conflicts ?? [],
    abstentionReason: dto.abstention_reason ?? "legacy_result_unverified",
    suggestedNextEvidence: dto.suggested_next_evidence ?? ["expert_review"],
    expertVerified: dto.expert_verified === true,
  };
}

export function applyGroundnutNutrientSafety(report: NutrientReport): NutrientReport {
  const groundnut = /^(groundnut|peanut|arachis hypogaea)$/i.test(
    (report.crop ?? "").trim(),
  );
  const groundnutSpecific = Boolean(groundnut && report.analysis?.primaryDeficiency);
  if (!groundnutSpecific || !report.analysis) return report;
  const evidenceRecommendations = report.recommendations.filter(
    (rec) => rec.category === "test" || rec.category === "expert",
  );
  if (!evidenceRecommendations.some((rec) => rec.category === "test")) {
    evidenceRecommendations.push({
      category: "test",
      code: "nutrient.rec.test.soil_test",
      nutrient: null,
      severity: "warning",
      priority: "medium",
    });
  }
  if (!evidenceRecommendations.some((rec) => rec.category === "expert")) {
    evidenceRecommendations.push({
      category: "expert",
      code: "nutrient.rec.expert.consult",
      nutrient: null,
      severity: "warning",
      priority: "medium",
    });
  }
  return {
    ...report,
    analysis: {
      ...report.analysis,
      status: report.analysis.resultCode === "abstained" ? "not_confirmed" : "possible",
      confidence: null,
      needsTest: true,
      needsExpert: true,
      explanationTamil: null,
      explanationEnglish: null,
      resultCode:
        report.analysis.resultCode === "abstained" ? "abstained" : "possible_finding",
      confidenceBand: null,
      suggestedNextEvidence: ["soil_or_tissue_test", "expert_review"],
      expertVerified: false,
    },
    recommendations: evidenceRecommendations,
  };
}

export function apiToReport(dto: ApiNutrientReport): NutrientReport {
  const mappedAnalysis = dto.analysis ? apiToAnalysis(dto.analysis) : null;
  return applyGroundnutNutrientSafety({
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
    analysis: mappedAnalysis,
    symptoms: dto.symptoms ?? [],
    recommendations: (dto.recommendations ?? []).map(apiToRecommendation),
    createdAt: dto.created_at,
  });
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
