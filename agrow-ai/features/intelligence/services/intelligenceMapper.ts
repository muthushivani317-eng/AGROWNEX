import type {
  ApiHealthScores,
  ApiIntelligenceDashboard,
  ApiIntelligenceHistoryEntry,
  ApiIntelligenceReport,
  HealthScores,
  IntelligenceDashboard,
  IntelligenceHistoryEntry,
  IntelligenceReport,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToHealth(dto: ApiHealthScores | null): HealthScores | null {
  if (!dto) return null;
  return {
    overallHealthScore: dto.overall_health_score,
    confidence: dto.confidence,
    diseaseScore: dto.disease_score,
    nutrientScore: dto.nutrient_score,
    soilScore: dto.soil_score,
    satelliteScore: dto.satellite_score,
    weatherScore: dto.weather_score,
    growthScore: dto.growth_score,
  };
}

export function apiToReport(dto: ApiIntelligenceReport): IntelligenceReport {
  const sourcesUsed = dto.sources_used ?? [];
  const hasSufficientEvidence = new Set(sourcesUsed).size >= 2;
  const health = apiToHealth(dto.health);
  if (health && !hasSufficientEvidence) health.overallHealthScore = null;
  return {
    id: dto.id,
    farmId: dto.farm_id,
    crop: dto.crop,
    generatedAt: dto.generated_at,
    overallHealthScore: hasSufficientEvidence ? dto.overall_health_score : null,
    confidence: dto.confidence,
    overallRisk: dto.overall_risk,
    riskScore: hasSufficientEvidence ? dto.risk_score : null,
    sourcesUsed,
    health,
    priorityIssues: (dto.priority_issues ?? []).map((i) => ({
      code: i.code,
      severity: i.severity,
      modules: i.modules ?? [],
    })),
    recommendations: (dto.recommendations ?? []).map((r) => ({
      code: r.code,
      priority: r.priority,
      category: r.category,
      modules: r.modules ?? [],
    })),
    createdAt: dto.created_at,
    isSample: false,
  };
}

export function apiToDashboard(dto: ApiIntelligenceDashboard): IntelligenceDashboard {
  return {
    farmId: dto.farm_id,
    hasData: dto.has_data,
    messageCode: dto.message_code,
    report: dto.report ? apiToReport(dto.report) : null,
  };
}

export function apiToHistoryEntry(dto: ApiIntelligenceHistoryEntry): IntelligenceHistoryEntry {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    reportId: dto.report_id,
    overallHealthScore: dto.overall_health_score,
    overallRisk: dto.overall_risk,
    confidence: dto.confidence,
    recordedAt: dto.recorded_at,
  };
}
