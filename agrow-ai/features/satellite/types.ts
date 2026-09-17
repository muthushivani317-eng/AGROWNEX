/**
 * Satellite Intelligence — professional farm monitoring over free Sentinel-2.
 * Imagery and vegetation indices are never fabricated: an unavailable scene is an
 * honest "Not Available" (docs/PRODUCT_RULES.md). Client-side camelCase mirror.
 */

export type SessionStatus =
  "available" | "unavailable" | "pending" | "processing";

export type UnavailableReason =
  | "none"
  | "no_polygon"
  | "cloud_cover"
  | "acquisition_delay"
  | "provider_error"
  | "no_imagery"
  | "provider_not_configured"
  | "provider_timeout"
  | "provider_rate_limited"
  | "processing_error";

export type VegetationHealth =
  "bare" | "very_low" | "low" | "moderate" | "good" | "very_good" | "unknown";

export type StressLevel = "none" | "mild" | "moderate" | "severe" | "unknown";

export type MoistureStatus =
  "very_dry" | "dry" | "adequate" | "moist" | "wet" | "unknown";

export type HealthTrend = "improving" | "stable" | "declining" | "unknown";

export type IndexName = "ndvi" | "ndre" | "evi" | "ndmi";

export type Severity = "info" | "advice" | "warning" | "critical";

export type WaterloggingDecision =
  | "observed_surface_water"
  | "clear"
  | "possible_waterlogging"
  | "possible_flood_risk"
  | "rainfall_risk_only"
  | "review_required"
  | "insufficient_data";

export interface WaterloggingAssessment {
  id: string;
  farmId: string;
  decision: WaterloggingDecision;
  observedAt: string | null;
  processedAt: string;
  source: string | null;
  aoiCoveragePct: number | null;
  evidencePresent: string[];
  evidenceMissing: string[];
  freshness: "current" | "stale" | "unknown";
  explanation: string;
  isSample: boolean;
  provenance: Record<string, unknown>;
  dataSource?: "live" | "cached" | "stale";
}

export interface ApiWaterloggingAssessment {
  id: string;
  farm_id: string;
  decision: WaterloggingDecision;
  observed_at: string | null;
  processed_at: string;
  source: string | null;
  aoi_coverage_pct: number | null;
  evidence_present: string[];
  evidence_missing: string[];
  freshness: "current" | "stale" | "unknown";
  explanation: string;
  is_sample: boolean;
  provenance: Record<string, unknown>;
}

export interface SatelliteIndex {
  indexName: string;
  mean: number | null;
  minimum: number | null;
  maximum: number | null;
  std: number | null;
}

export interface SatelliteImage {
  id: string;
  band: string;
  imageUrl: string;
  thumbnailUrl: string | null;
  resolutionM: number | null;
}

export interface SatelliteAlert {
  code: string;
  category: string;
  severity: Severity;
  priority: string;
  value: number | null;
  params: Record<string, unknown>;
}

export interface SatelliteSession {
  id: string;
  farmId: string;
  provider: string;
  status: SessionStatus;
  unavailableReason: UnavailableReason;
  isSample: boolean;
  captureDate: string | null;
  cloudCover: number | null;
  resolutionM: number | null;
  ndvi: number | null;
  ndre: number | null;
  evi: number | null;
  ndmi: number | null;
  vegetationHealth: string | null;
  stressLevel: string | null;
  moistureStatus: string | null;
  trend: string | null;
  ndviDelta: number | null;
  confidence: number;
  metadata: Record<string, unknown> | null;
  createdAt: string;
  images: SatelliteImage[];
  indices: SatelliteIndex[];
  alerts: SatelliteAlert[];
}

export interface SatelliteDashboard {
  farmId: string;
  hasPolygon: boolean;
  hasData: boolean;
  status: SessionStatus;
  unavailableReason: UnavailableReason;
  messageCode: string | null;
  session: SatelliteSession | null;
  alerts: SatelliteAlert[];
  dataSource?: "live" | "cached" | "stale";
}

export interface SatelliteReadiness {
  provider_configured: boolean;
  storage_configured: boolean;
  public_delivery_configured: boolean;
  queue_configured: boolean;
  ready_for_image_generation: boolean;
  missing_components: string[];
}

export interface SatelliteHistoryEntry {
  id: string;
  farmId: string;
  sessionId: string | null;
  captureDate: string | null;
  ndvi: number | null;
  ndre: number | null;
  evi: number | null;
  ndmi: number | null;
  vegetationHealth: string | null;
  stressLevel: string | null;
  moistureStatus: string | null;
  source: string;
  confidence: number;
  recordedAt: string;
}

export interface TimelinePoint {
  period: string;
  ndvi: number | null;
  ndre: number | null;
  ndmi: number | null;
  count: number;
}

export interface SatelliteTimeline {
  farmId: string;
  range: string;
  points: TimelinePoint[];
}

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiSatelliteIndex {
  index_name: string;
  mean: number | null;
  minimum: number | null;
  maximum: number | null;
  std: number | null;
}

export interface ApiSatelliteImage {
  id: string;
  band: string;
  image_url: string;
  thumbnail_url: string | null;
  resolution_m: number | null;
}

export interface ApiSatelliteAlert {
  code: string;
  category: string;
  severity: Severity;
  priority: string;
  value: number | null;
  params: Record<string, unknown>;
}

export interface ApiSatelliteSession {
  id: string;
  farm_id: string;
  provider: string;
  status: SessionStatus;
  unavailable_reason: UnavailableReason;
  is_sample: boolean;
  capture_date: string | null;
  cloud_cover: number | null;
  resolution_m: number | null;
  ndvi: number | null;
  ndre: number | null;
  evi: number | null;
  ndmi: number | null;
  vegetation_health: string | null;
  stress_level: string | null;
  moisture_status: string | null;
  trend: string | null;
  ndvi_delta: number | null;
  confidence: number;
  metadata: Record<string, unknown> | null;
  created_at: string;
  images: ApiSatelliteImage[];
  indices: ApiSatelliteIndex[];
  alerts: ApiSatelliteAlert[];
}

export interface ApiSatelliteDashboard {
  farm_id: string;
  has_polygon: boolean;
  has_data: boolean;
  status: SessionStatus;
  unavailable_reason: UnavailableReason;
  message_code: string | null;
  session: ApiSatelliteSession | null;
  alerts: ApiSatelliteAlert[];
}

export interface ApiSatelliteHistoryEntry {
  id: string;
  farm_id: string;
  session_id: string | null;
  capture_date: string | null;
  ndvi: number | null;
  ndre: number | null;
  evi: number | null;
  ndmi: number | null;
  vegetation_health: string | null;
  stress_level: string | null;
  moisture_status: string | null;
  source: string;
  confidence: number;
  recorded_at: string;
}

export interface ApiTimelinePoint {
  period: string;
  ndvi: number | null;
  ndre: number | null;
  ndmi: number | null;
  count: number;
}

export interface ApiSatelliteTimeline {
  farm_id: string;
  range: string;
  points: ApiTimelinePoint[];
}
