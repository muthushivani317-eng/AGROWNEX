import type { SupportedLanguage } from "@/types";

/**
 * Nutrient Deficiency AI domain types (camelCase mirror of the backend schemas).
 * A deficiency is never fabricated: an unconfirmed finding is ``not_confirmed`` and
 * an unavailable value is ``null`` (docs/PRODUCT_RULES.md).
 */

export type DeficiencyStatus = "confirmed" | "possible" | "not_confirmed";
export type Severity = "none" | "mild" | "moderate" | "severe" | "unknown";
export type CaptureMethod = "camera" | "gallery";
export type NutrientResultCode =
  | "supported_finding"
  | "possible_finding"
  | "abstained"
  | "invalid_image"
  | "crop_mismatch"
  | "unsupported_crop"
  | "provider_unavailable";

export type Nutrient =
  | "nitrogen"
  | "phosphorus"
  | "potassium"
  | "sulphur"
  | "calcium"
  | "magnesium"
  | "iron"
  | "zinc"
  | "boron"
  | "copper"
  | "manganese"
  | "molybdenum"
  | "chlorine";

export interface NutrientRecommendation {
  category: string;
  code: string;
  nutrient: string | null;
  severity: string;
  priority: string;
}

export interface NutrientAnalysis {
  primaryDeficiency: string | null;
  secondaryDeficiency: string | null;
  status: DeficiencyStatus;
  confidence: number;
  severity: Severity;
  affectedArea: string | null;
  diseaseConflict: boolean;
  needsTest: boolean;
  needsExpert: boolean;
  soilReference: Record<string, unknown> | null;
  satelliteReference: Record<string, unknown> | null;
  weatherReference: Record<string, unknown> | null;
  explanationTamil: string | null;
  explanationEnglish: string | null;
  resultCode: NutrientResultCode;
  confidenceBand: "low" | "medium" | "high";
  evidenceObserved: string[];
  evidenceMissing: string[];
  conflicts: string[];
  abstentionReason: string | null;
  suggestedNextEvidence: string[];
  expertVerified: boolean;
}

export interface NutrientReport {
  id: string;
  farmId: string;
  crop: string | null;
  imageUrl: string;
  thumbnailUrl: string | null;
  captureDate: string | null;
  provider: string;
  modelUsed: string | null;
  status: string;
  language: SupportedLanguage;
  latitude: number | null;
  longitude: number | null;
  weatherSnapshot: Record<string, unknown> | null;
  analysis: NutrientAnalysis | null;
  symptoms: string[];
  recommendations: NutrientRecommendation[];
  createdAt: string;
}

export interface NutrientHistoryEntry {
  id: string;
  farmId: string;
  reportId: string | null;
  crop: string | null;
  primaryDeficiency: string | null;
  status: DeficiencyStatus;
  confidence: number;
  severity: Severity | null;
  recordedAt: string;
}

export interface AnalyzeInput {
  imageBase64: string;
  mimeType: string;
  imageUri: string;
  language: SupportedLanguage;
  captureMethod: CaptureMethod;
  farmId: string;
  crop?: string | null;
  latitude?: number | null;
  longitude?: number | null;
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
export interface ApiNutrientRecommendation {
  category: string;
  code: string;
  nutrient: string | null;
  severity: string;
  priority: string;
}

export interface ApiNutrientAnalysis {
  primary_deficiency: string | null;
  secondary_deficiency: string | null;
  status: DeficiencyStatus;
  confidence: number;
  severity: Severity;
  affected_area: string | null;
  disease_conflict: boolean;
  needs_test: boolean;
  needs_expert: boolean;
  soil_reference: Record<string, unknown> | null;
  satellite_reference: Record<string, unknown> | null;
  weather_reference: Record<string, unknown> | null;
  explanation_tamil: string | null;
  explanation_english: string | null;
  result_code?: NutrientResultCode;
  confidence_band?: "low" | "medium" | "high";
  evidence_observed?: string[];
  evidence_missing?: string[];
  conflicts?: string[];
  abstention_reason?: string | null;
  suggested_next_evidence?: string[];
  expert_verified?: boolean;
}

export interface ApiNutrientReport {
  id: string;
  farm_id: string;
  crop: string | null;
  image_url: string;
  thumbnail_url: string | null;
  capture_date: string | null;
  provider: string;
  model_used: string | null;
  status: string;
  language: string;
  latitude: number | null;
  longitude: number | null;
  weather_snapshot: Record<string, unknown> | null;
  analysis: ApiNutrientAnalysis | null;
  symptoms: string[];
  recommendations: ApiNutrientRecommendation[];
  created_at: string;
}

export interface ApiNutrientHistoryEntry {
  id: string;
  farm_id: string;
  report_id: string | null;
  crop: string | null;
  primary_deficiency: string | null;
  status: DeficiencyStatus;
  confidence: number;
  severity: Severity | null;
  recorded_at: string;
}
