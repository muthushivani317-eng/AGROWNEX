/**
 * Soil Intelligence — location + farmer-report soil insights (future-ready).
 * Generic agronomic advice only; soil values are never fabricated
 * (docs/PRODUCT_RULES.md). Client-side camelCase mirror of the backend schemas.
 */

export type SoilSource =
  | "self"
  | "soil_health_card"
  | "lab"
  | "government"
  | "satellite"
  | "farm_registration"
  | "estimate";

export type ReportStatus = "submitted" | "processed";

export type RatingLevel = "low" | "medium" | "high" | "optimal" | "unknown";

export type PhClass =
  | "strongly_acidic"
  | "acidic"
  | "neutral"
  | "alkaline"
  | "strongly_alkaline"
  | "unknown";

export type DrainageClass = "poor" | "moderate" | "good" | "excessive";

export type Severity = "info" | "advice" | "warning" | "critical";

export interface SoilValues {
  ph?: number | null;
  organicCarbon?: number | null;
  nitrogen?: number | null;
  phosphorus?: number | null;
  potassium?: number | null;
  sulphur?: number | null;
  ecSalinity?: number | null;
  waterHoldingCapacity?: number | null;
  drainage?: DrainageClass | null;
  micronutrients?: Record<string, number> | null;
}

export interface SoilProfile {
  id: string;
  farmId: string;
  soilType: string | null;
  latitude: number | null;
  longitude: number | null;
  ph: number | null;
  organicCarbon: number | null;
  nitrogen: number | null;
  phosphorus: number | null;
  potassium: number | null;
  micronutrients: Record<string, number> | null;
  ecSalinity: number | null;
  waterHoldingCapacity: number | null;
  drainage: string | null;
  source: string;
  confidence: number;
  lastTestDate: string | null;
  updatedAt: string | null;
}

export interface SoilTestResult {
  ph: number | null;
  organicCarbon: number | null;
  nitrogen: number | null;
  phosphorus: number | null;
  potassium: number | null;
  sulphur: number | null;
  ecSalinity: number | null;
  waterHoldingCapacity: number | null;
  drainage: string | null;
  micronutrients: Record<string, number> | null;
}

export interface SoilReport {
  id: string;
  farmId: string;
  source: string;
  reportUrl: string | null;
  thumbnailUrl: string | null;
  labName: string | null;
  testDate: string | null;
  notes: string | null;
  status: ReportStatus;
  confidence: number;
  createdAt: string;
  result: SoilTestResult | null;
}

export interface SoilAssessment {
  phClass: string;
  organicCarbon: string;
  nitrogen: string;
  phosphorus: string;
  potassium: string;
  salinity: string;
  deficientMicronutrients: string[];
  hasAnyValue: boolean;
}

export interface SoilRecommendation {
  category: string;
  code: string;
  parameter: string | null;
  rating: string | null;
  severity: Severity;
  priority: string;
  value: number | null;
  unit: string | null;
}

export interface SoilHistoryEntry {
  id: string;
  farmId: string;
  reportId: string | null;
  testDate: string | null;
  ph: number | null;
  organicCarbon: number | null;
  nitrogen: number | null;
  phosphorus: number | null;
  potassium: number | null;
  source: string;
  confidence: number;
  recordedAt: string;
}

export interface SoilDashboard {
  farmId: string;
  hasData: boolean;
  messageCode: string | null;
  profile: SoilProfile | null;
  assessment: SoilAssessment | null;
  recommendations: SoilRecommendation[];
  latestReport: SoilReport | null;
  indicatorEvidence: SoilIndicatorEvidence[];
  overallStatus: string;
  laboratoryEquivalent: false;
}

export interface SoilIndicatorEvidence {
  indicator: string;
  value: number | string;
  unit: string;
  evidenceType: string;
  collectionMethod: string;
  collectedAt: string;
  sourceReference: string;
  spatialCoverage: string;
  confidence: number | null;
  uncertaintyLow: number | null;
  uncertaintyHigh: number | null;
  verificationState: string;
  freshness: string;
  status: string;
  reportReference: string | null;
}

export interface SoilReportInput {
  farmId: string;
  source?: SoilSource;
  reportUrl?: string | null;
  thumbnailUrl?: string | null;
  mimeType?: string | null;
  labName?: string | null;
  testDate?: string | null;
  notes?: string | null;
  values: SoilValues;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface RemoteSoilOutcome {
  status: string;
  reason: string;
  estimates: Array<{
    indicator: string;
    value: number;
    unit: string;
    provider: string;
    modelVersion: string;
  }>;
}

export interface ApiRemoteSoilOutcome {
  status: string;
  reason: string;
  estimates: Array<{
    indicator: string;
    value: number;
    unit: string;
    provider: string;
    model_version: string;
  }>;
}

export interface ApiSoilScan {
  id?: string;
  farm_id: string;
  aoi_verified: boolean;
  aoi_geojson?: { type: "Polygon"; coordinates: number[][][] } | null;
  generated_at: string;
  provider_states?: Record<string, string>;
  provenance?: Record<string, unknown>;
  indicators: Array<{
    code: string;
    status: string;
    evidence_class: string;
    value: string | number | null;
    explanation_code: string;
    details: Record<string, unknown>;
    sampling_points: Array<{
      zone_id: string;
      longitude: number;
      latitude: number;
      source: string;
      reference?: string | null;
      reason?: string;
      quality?: string;
      sample_data: false;
    }>;
    sources?: string[];
    observation_timestamps?: string[];
    missing_evidence?: string[];
  }>;
  sampling_plan?: {
    id: string;
    status: string;
    created_at: string;
    scope: string;
    points: ApiSoilScan["indicators"][number]["sampling_points"];
  } | null;
}
export interface SoilScan {
  id: string;
  farmId: string;
  aoiVerified: boolean;
  aoiGeojson: { type: "Polygon"; coordinates: number[][][] } | null;
  generatedAt: string;
  providerStates: Record<string, string>;
  provenance: Record<string, unknown>;
  indicators: Array<{
    code: string;
    status: string;
    evidenceClass: string;
    value: string | number | null;
    explanationCode: string;
    details: Record<string, unknown>;
    samplingPoints: Array<{
      zoneId: string;
      longitude: number;
      latitude: number;
      source: string;
      reference: string | null;
      reason: string;
      quality: string;
      sampleData: false;
    }>;
    sources: string[];
    observationTimestamps: string[];
    missingEvidence: string[];
  }>;
  samplingPlan: {
    id: string;
    status: string;
    createdAt: string;
    scope: string;
    points: SoilScan["indicators"][number]["samplingPoints"];
  } | null;
  cacheState?: "live" | "cached";
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiSoilTestResult {
  ph: number | null;
  organic_carbon: number | null;
  nitrogen: number | null;
  phosphorus: number | null;
  potassium: number | null;
  sulphur: number | null;
  ec_salinity: number | null;
  water_holding_capacity: number | null;
  drainage: string | null;
  micronutrients: Record<string, number> | null;
}

export interface ApiSoilReport {
  id: string;
  farm_id: string;
  source: string;
  report_url: string | null;
  thumbnail_url: string | null;
  lab_name: string | null;
  test_date: string | null;
  notes: string | null;
  status: ReportStatus;
  confidence: number;
  created_at: string;
  result: ApiSoilTestResult | null;
}

export interface ApiSoilProfile {
  id: string;
  farm_id: string;
  soil_type: string | null;
  latitude: number | null;
  longitude: number | null;
  ph: number | null;
  organic_carbon: number | null;
  nitrogen: number | null;
  phosphorus: number | null;
  potassium: number | null;
  micronutrients: Record<string, number> | null;
  ec_salinity: number | null;
  water_holding_capacity: number | null;
  drainage: string | null;
  source: string;
  confidence: number;
  last_test_date: string | null;
  updated_at: string | null;
}

export interface ApiSoilAssessment {
  ph_class: string;
  organic_carbon: string;
  nitrogen: string;
  phosphorus: string;
  potassium: string;
  salinity: string;
  deficient_micronutrients: string[];
  has_any_value: boolean;
}

export interface ApiSoilRecommendation {
  category: string;
  code: string;
  parameter: string | null;
  rating: string | null;
  severity: Severity;
  priority: string;
  value: number | null;
  unit: string | null;
}

export interface ApiSoilHistoryEntry {
  id: string;
  farm_id: string;
  report_id: string | null;
  test_date: string | null;
  ph: number | null;
  organic_carbon: number | null;
  nitrogen: number | null;
  phosphorus: number | null;
  potassium: number | null;
  source: string;
  confidence: number;
  recorded_at: string;
}

export interface ApiSoilDashboard {
  farm_id: string;
  has_data: boolean;
  message_code: string | null;
  profile: ApiSoilProfile | null;
  assessment: ApiSoilAssessment | null;
  recommendations: ApiSoilRecommendation[];
  latest_report: ApiSoilReport | null;
  indicator_evidence?: ApiSoilIndicatorEvidence[];
  overall_status?: string;
  laboratory_equivalent?: boolean;
}

export interface ApiSoilIndicatorEvidence {
  indicator: string;
  value: number | string;
  unit: string;
  evidence_type: string;
  collection_method: string;
  collected_at: string;
  source_reference: string;
  spatial_coverage: string;
  confidence: number | null;
  uncertainty_low: number | null;
  uncertainty_high: number | null;
  verification_state: string;
  freshness: string;
  status: string;
  report_reference: string | null;
}
