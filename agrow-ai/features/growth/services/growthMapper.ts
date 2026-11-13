import type {
  ApiStageState,
  StageState,
  ApiGrowthAnalysis,
  ApiGrowthImage,
  ApiGrowthSession,
  ApiGrowthSessionDetail,
  ApiGrowthTimeline,
  ApiTimelineEntry,
  ApiUploadResult,
  GrowthAnalysis,
  GrowthImage,
  GrowthSession,
  GrowthSessionDetail,
  GrowthTimeline,
  TimelineEntry,
  UploadResult,
} from "../types";

export const apiToStageState = (dto: ApiStageState): StageState => ({
  id: dto.id,
  farmId: dto.farm_id,
  cropCycleId: dto.crop_cycle_id,
  state: dto.state,
  suggestedStage: dto.suggested_stage,
  confirmedStage: dto.confirmed_stage,
  registryVersion: dto.registry_version,
  calculationVersion: dto.calculation_version,
  version: dto.version,
  pendingSync: dto.pending_sync,
  evidenceSnapshot: dto.evidence_snapshot,
  updatedAt: dto.updated_at,
});

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToAnalysis(
  dto: ApiGrowthAnalysis | null,
): GrowthAnalysis | null {
  if (!dto) return null;
  return {
    growthStage: dto.growth_stage,
    plantVigor: dto.plant_vigor,
    healthScore: dto.health_score,
    confidence: dto.confidence,
    leafColorObservations: dto.leaf_color_observations ?? [],
    visibleAbnormalities: dto.visible_abnormalities ?? [],
    changesFromPrevious: dto.changes_from_previous ?? [],
    recommendations: dto.recommendations ?? [],
    diseaseResult: dto.disease_result,
    nutrientResult: dto.nutrient_result,
    needsExpertReview: dto.needs_expert_review,
    growthSummaryTamil: dto.growth_summary_tamil,
    growthSummaryEnglish: dto.growth_summary_english,
    modelUsed: dto.model_used,
  };
}

export function apiToImage(dto: ApiGrowthImage): GrowthImage {
  return {
    id: dto.id,
    sessionId: dto.session_id,
    farmId: dto.farm_id,
    imageUrl: dto.image_url,
    thumbnailUrl: dto.thumbnail_url,
    captureMethod: dto.capture_method,
    capturedAt: dto.captured_at,
    weekNumber: dto.week_number,
    latitude: dto.latitude,
    longitude: dto.longitude,
    weatherSnapshot: dto.weather_snapshot
      ? {
          condition: dto.weather_snapshot.condition as string | undefined,
          temperatureC:
            (dto.weather_snapshot.temperature_c as number | null) ?? null,
          humidityPct:
            (dto.weather_snapshot.humidity_pct as number | null) ?? null,
          windSpeedKmh:
            (dto.weather_snapshot.wind_speed_kmh as number | null) ?? null,
          fetchedAt: dto.weather_snapshot.fetched_at as string | undefined,
        }
      : null,
    imageQuality: dto.image_quality,
    notes: dto.notes,
    createdAt: dto.created_at,
    analysis: apiToAnalysis(dto.analysis),
  };
}

export function apiToTimelineEntry(dto: ApiTimelineEntry): TimelineEntry {
  return {
    id: dto.id,
    sessionId: dto.session_id,
    imageId: dto.image_id,
    weekNumber: dto.week_number,
    growthStage: dto.growth_stage,
    healthScore: dto.health_score,
    healthDelta: dto.health_delta,
    riskLevel: dto.risk_level,
    summary: dto.summary,
    recordedAt: dto.recorded_at,
    imageUrl: dto.image_url,
    thumbnailUrl: dto.thumbnail_url,
  };
}

export function apiToSession(dto: ApiGrowthSession): GrowthSession {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    crop: dto.crop,
    variety: dto.variety,
    title: dto.title,
    sowingDate: dto.sowing_date,
    status: dto.status,
    currentGrowthStage: dto.current_growth_stage,
    latestHealthScore: dto.latest_health_score,
    latestRiskLevel: dto.latest_risk_level,
    imageCount: dto.image_count,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function apiToSessionDetail(
  dto: ApiGrowthSessionDetail,
): GrowthSessionDetail {
  return {
    ...apiToSession(dto),
    images: (dto.images ?? []).map(apiToImage),
    timeline: (dto.timeline ?? []).map(apiToTimelineEntry),
  };
}

export function apiToTimeline(dto: ApiGrowthTimeline): GrowthTimeline {
  return {
    session: apiToSession(dto.session),
    timeline: (dto.timeline ?? []).map(apiToTimelineEntry),
  };
}

export function apiToUploadResult(dto: ApiUploadResult): UploadResult {
  return {
    session: apiToSession(dto.session),
    image: apiToImage(dto.image),
    timelineEntry: apiToTimelineEntry(dto.timeline_entry),
    stageComparison: dto.stage_comparison
      ? {
          geminiStage: dto.stage_comparison.gemini_stage,
          calendarStage: dto.stage_comparison.calendar_stage,
          expectedGeminiStages: dto.stage_comparison.expected_gemini_stages,
          mismatch: dto.stage_comparison.mismatch,
          warningCode: dto.stage_comparison.warning_code,
        }
      : null,
  };
}
