import type {
  ApiSatelliteAlert,
  ApiSatelliteDashboard,
  ApiSatelliteHistoryEntry,
  ApiSatelliteImage,
  ApiSatelliteIndex,
  ApiSatelliteSession,
  ApiSatelliteTimeline,
  SatelliteAlert,
  SatelliteDashboard,
  SatelliteHistoryEntry,
  SatelliteImage,
  SatelliteIndex,
  SatelliteSession,
  SatelliteTimeline,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToIndex(dto: ApiSatelliteIndex): SatelliteIndex {
  return {
    indexName: dto.index_name,
    mean: dto.mean,
    minimum: dto.minimum,
    maximum: dto.maximum,
    std: dto.std,
  };
}

export function apiToImage(dto: ApiSatelliteImage): SatelliteImage {
  return {
    id: dto.id,
    band: dto.band,
    imageUrl: dto.image_url,
    thumbnailUrl: dto.thumbnail_url,
    resolutionM: dto.resolution_m,
  };
}

export function apiToAlert(dto: ApiSatelliteAlert): SatelliteAlert {
  return {
    code: dto.code,
    category: dto.category,
    severity: dto.severity,
    priority: dto.priority,
    value: dto.value,
    params: dto.params ?? {},
  };
}

export function apiToSession(dto: ApiSatelliteSession): SatelliteSession {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    provider: dto.provider,
    status: dto.status,
    unavailableReason: dto.unavailable_reason,
    isSample: dto.is_sample,
    captureDate: dto.capture_date,
    cloudCover: dto.cloud_cover,
    resolutionM: dto.resolution_m,
    ndvi: dto.ndvi,
    ndre: dto.ndre,
    evi: dto.evi,
    ndmi: dto.ndmi,
    vegetationHealth: dto.vegetation_health,
    stressLevel: dto.stress_level,
    moistureStatus: dto.moisture_status,
    trend: dto.trend,
    ndviDelta: dto.ndvi_delta,
    confidence: dto.confidence,
    metadata: dto.metadata,
    createdAt: dto.created_at,
    images: (dto.images ?? []).map(apiToImage),
    indices: (dto.indices ?? []).map(apiToIndex),
    alerts: (dto.alerts ?? []).map(apiToAlert),
  };
}

export function apiToDashboard(dto: ApiSatelliteDashboard): SatelliteDashboard {
  return {
    farmId: dto.farm_id,
    hasPolygon: dto.has_polygon,
    hasData: dto.has_data,
    status: dto.status,
    unavailableReason: dto.unavailable_reason,
    messageCode: dto.message_code,
    session: dto.session ? apiToSession(dto.session) : null,
    alerts: (dto.alerts ?? []).map(apiToAlert),
  };
}

export function apiToHistoryEntry(dto: ApiSatelliteHistoryEntry): SatelliteHistoryEntry {
  return {
    id: dto.id,
    farmId: dto.farm_id,
    sessionId: dto.session_id,
    captureDate: dto.capture_date,
    ndvi: dto.ndvi,
    ndre: dto.ndre,
    evi: dto.evi,
    ndmi: dto.ndmi,
    vegetationHealth: dto.vegetation_health,
    stressLevel: dto.stress_level,
    moistureStatus: dto.moisture_status,
    source: dto.source,
    confidence: dto.confidence,
    recordedAt: dto.recorded_at,
  };
}

export function apiToTimeline(dto: ApiSatelliteTimeline): SatelliteTimeline {
  return {
    farmId: dto.farm_id,
    range: dto.range,
    points: (dto.points ?? []).map((p) => ({
      period: p.period,
      ndvi: p.ndvi,
      ndre: p.ndre,
      ndmi: p.ndmi,
      count: p.count,
    })),
  };
}
