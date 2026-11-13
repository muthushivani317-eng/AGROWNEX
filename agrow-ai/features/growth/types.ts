import type { SupportedLanguage } from "@/types";

/**
 * Crop Growth Monitor domain types (docs/API_CONTRACT.md → CROP GROWTH).
 * Client-side camelCase mirror of the backend growth schemas. Stage/vigour are
 * stable codes the Tamil-first UI localizes; summaries carry the AI text.
 */

export type GrowthStage =
  | "germination"
  | "seedling"
  | "vegetative"
  | "flowering"
  | "fruiting"
  | "maturity"
  | "harvest"
  | "unknown";

export type PlantVigor = "poor" | "fair" | "good" | "excellent" | "unknown";
export type RiskLevel = "low" | "moderate" | "high";
export type CaptureMethod = "camera" | "gallery";
export type StageTrackingState =
  | "not_started"
  | "stage_unknown"
  | "stage_suggested"
  | "awaiting_confirmation"
  | "confirmed"
  | "uncertain"
  | "corrected"
  | "completed";

export interface StageState {
  id: string;
  farmId: string;
  cropCycleId: string;
  state: StageTrackingState;
  suggestedStage: GrowthStage | null;
  confirmedStage: GrowthStage | null;
  registryVersion: string | null;
  calculationVersion: string;
  version: number;
  pendingSync: boolean;
  evidenceSnapshot: Record<string, unknown>;
  updatedAt: string;
}

export interface ApiStageState {
  id: string;
  farm_id: string;
  crop_cycle_id: string;
  state: StageTrackingState;
  suggested_stage: GrowthStage | null;
  confirmed_stage: GrowthStage | null;
  registry_version: string | null;
  calculation_version: string;
  version: number;
  pending_sync: boolean;
  evidence_snapshot: Record<string, unknown>;
  updated_at: string;
}

export interface StageTransitionInput {
  farmId: string;
  cropCycleId: string;
  event: "evaluate" | "confirm" | "correct" | "complete";
  stage?: GrowthStage | null;
  expectedVersion?: number | null;
  idempotencyKey: string;
  reason?: string | null;
}

export interface StageTransitionHistory {
  id: string;
  event: string;
  priorState: string | null;
  nextState: string;
  priorStage: GrowthStage | null;
  stage: GrowthStage | null;
  reason: string | null;
  expertReviewed: boolean;
  createdAt: string;
}

export interface ApiStageTransitionHistory {
  id: string;
  event: string;
  prior_state: string | null;
  next_state: string;
  prior_stage: GrowthStage | null;
  stage: GrowthStage | null;
  reason: string | null;
  expert_reviewed: boolean;
  created_at: string;
}

export interface WeatherSnapshot {
  condition?: string;
  temperatureC?: number | null;
  humidityPct?: number | null;
  windSpeedKmh?: number | null;
  fetchedAt?: string;
}

export interface GrowthAnalysis {
  growthStage: GrowthStage;
  plantVigor: PlantVigor;
  healthScore: number | null;
  confidence: number | null;
  leafColorObservations: string[];
  visibleAbnormalities: string[];
  changesFromPrevious: string[];
  recommendations: string[];
  diseaseResult: Record<string, unknown> | null;
  nutrientResult: Record<string, unknown> | null;
  needsExpertReview: boolean;
  growthSummaryTamil: string | null;
  growthSummaryEnglish: string | null;
  modelUsed: string | null;
}

export interface GrowthImage {
  id: string;
  sessionId: string;
  farmId: string | null;
  imageUrl: string;
  thumbnailUrl: string | null;
  captureMethod: CaptureMethod;
  capturedAt: string;
  weekNumber: number;
  latitude: number | null;
  longitude: number | null;
  weatherSnapshot: WeatherSnapshot | null;
  imageQuality: Record<string, unknown> | null;
  notes: string | null;
  createdAt: string;
  analysis: GrowthAnalysis | null;
}

export interface TimelineEntry {
  id: string;
  sessionId: string;
  imageId: string;
  weekNumber: number;
  growthStage: GrowthStage;
  healthScore: number | null;
  healthDelta: number | null;
  riskLevel: RiskLevel;
  summary: string | null;
  recordedAt: string;
  imageUrl: string | null;
  thumbnailUrl: string | null;
}

export interface GrowthSession {
  id: string;
  farmId: string;
  crop: string | null;
  variety: string | null;
  title: string | null;
  sowingDate: string | null;
  status: string;
  currentGrowthStage: GrowthStage;
  latestHealthScore: number | null;
  latestRiskLevel: RiskLevel | null;
  imageCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface GrowthSessionDetail extends GrowthSession {
  images: GrowthImage[];
  timeline: TimelineEntry[];
}

export interface GrowthTimeline {
  session: GrowthSession;
  timeline: TimelineEntry[];
}

export interface UploadResult {
  session: GrowthSession;
  image: GrowthImage;
  timelineEntry: TimelineEntry;
  stageComparison: GroundnutStageComparison | null;
}

export interface GroundnutStageComparison {
  geminiStage: GrowthStage;
  calendarStage: string;
  expectedGeminiStages: GrowthStage[];
  mismatch: boolean;
  warningCode: string | null;
}

export interface GroundnutStageDecisionInput {
  sessionId: string;
  imageId: string;
  action: "confirm" | "correct";
  stage: Exclude<GrowthStage, "unknown">;
}

export interface UploadGrowthInput {
  imageBase64: string;
  mimeType: string;
  imageUri: string;
  farmId: string;
  sessionId?: string | null;
  crop?: string | null;
  variety?: string | null;
  language: SupportedLanguage;
  captureMethod: CaptureMethod;
  latitude?: number | null;
  longitude?: number | null;
  notes?: string | null;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiGrowthAnalysis {
  growth_stage: GrowthStage;
  plant_vigor: PlantVigor;
  health_score: number | null;
  confidence: number | null;
  leaf_color_observations: string[];
  visible_abnormalities: string[];
  changes_from_previous: string[];
  recommendations: string[];
  disease_result: Record<string, unknown> | null;
  nutrient_result: Record<string, unknown> | null;
  needs_expert_review: boolean;
  growth_summary_tamil: string | null;
  growth_summary_english: string | null;
  model_used: string | null;
}

export interface ApiGrowthImage {
  id: string;
  session_id: string;
  farm_id: string | null;
  image_url: string;
  thumbnail_url: string | null;
  capture_method: CaptureMethod;
  captured_at: string;
  week_number: number;
  latitude: number | null;
  longitude: number | null;
  weather_snapshot: Record<string, unknown> | null;
  image_quality: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
  analysis: ApiGrowthAnalysis | null;
}

export interface ApiTimelineEntry {
  id: string;
  session_id: string;
  image_id: string;
  week_number: number;
  growth_stage: GrowthStage;
  health_score: number | null;
  health_delta: number | null;
  risk_level: RiskLevel;
  summary: string | null;
  recorded_at: string;
  image_url: string | null;
  thumbnail_url: string | null;
}

export interface ApiGrowthSession {
  id: string;
  farm_id: string;
  crop: string | null;
  variety: string | null;
  title: string | null;
  sowing_date: string | null;
  status: string;
  current_growth_stage: GrowthStage;
  latest_health_score: number | null;
  latest_risk_level: RiskLevel | null;
  image_count: number;
  created_at: string;
  updated_at: string;
}

export interface ApiGrowthSessionDetail extends ApiGrowthSession {
  images: ApiGrowthImage[];
  timeline: ApiTimelineEntry[];
}

export interface ApiGrowthTimeline {
  session: ApiGrowthSession;
  timeline: ApiTimelineEntry[];
}

export interface ApiUploadResult {
  session: ApiGrowthSession;
  image: ApiGrowthImage;
  timeline_entry: ApiTimelineEntry;
  stage_comparison?: {
    gemini_stage: GrowthStage;
    calendar_stage: string;
    expected_gemini_stages: GrowthStage[];
    mismatch: boolean;
    warning_code: string | null;
  } | null;
}

/** "Behind schedule" = an overdue organic task OR stage lagging the crop calendar. */
export type GrowthScheduleReason = "overdue_task" | "stage_lagging";

export interface GrowthScheduleStatus {
  behind: boolean;
  reasons: GrowthScheduleReason[];
  overdueTasks: number;
  expectedStage: GrowthStage | null;
  observedStage: GrowthStage | null;
}
