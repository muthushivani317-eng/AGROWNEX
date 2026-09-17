import type {
  ApiFarmMemory,
  ApiMemoryDashboard,
  ApiMemoryLink,
  ApiMemorySummary,
  ApiMemorySummaryBundle,
  FarmMemory,
  MemoryDashboard,
  MemoryLink,
  MemorySummary,
  MemorySummaryBundle,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToLink(dto: ApiMemoryLink): MemoryLink {
  return {
    id: dto.id,
    fromMemoryId: dto.from_memory_id,
    toMemoryId: dto.to_memory_id,
    linkType: dto.link_type,
  };
}

export function apiToMemory(dto: ApiFarmMemory): FarmMemory {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    sourceModule: dto.source_module,
    eventType: dto.event_type,
    summary: dto.summary,
    params: dto.params,
    confidence: dto.confidence,
    importance: dto.importance,
    importanceScore: dto.importance_score,
    observation: dto.observation,
    season: dto.season,
    seasonYear: dto.season_year,
    crop: dto.crop,
    location: dto.location,
    occurredAt: dto.occurred_at,
    createdAt: dto.created_at,
    tags: dto.tags ?? [],
    occurrences: dto.occurrences,
    links: (dto.links ?? []).map(apiToLink),
    isSample: false,
  };
}

export function apiToSummary(dto: ApiMemorySummary): MemorySummary {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    periodType: dto.period_type,
    periodKey: dto.period_key,
    season: dto.season,
    year: dto.year,
    crop: dto.crop,
    summary: dto.summary,
    params: dto.params,
    highlights: dto.highlights ?? [],
    eventCount: dto.event_count,
    importance: dto.importance,
    generatedAt: dto.generated_at,
  };
}

export function apiToDashboard(dto: ApiMemoryDashboard): MemoryDashboard {
  return {
    farmId: dto.farm_id,
    hasData: dto.has_data,
    total: dto.total,
    messageCode: dto.message_code,
    recent: (dto.recent ?? []).map(apiToMemory),
    latestSummary: dto.latest_summary ? apiToSummary(dto.latest_summary) : null,
  };
}

export function apiToSummaryBundle(dto: ApiMemorySummaryBundle): MemorySummaryBundle {
  return {
    farmId: dto.farm_id,
    seasons: (dto.seasons ?? []).map(apiToSummary),
    years: (dto.years ?? []).map(apiToSummary),
  };
}
