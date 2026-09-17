import type { SupportedLanguage } from '@/types';

/**
 * Disease Detection domain types (docs/API_CONTRACT.md → DISEASE).
 * Client-side camelCase mirror of the backend disease schemas.
 */

export type Severity = 'none' | 'low' | 'moderate' | 'high';
export type CaptureMethod = 'camera' | 'gallery';

/** A locally-picked image ready for the quality gate + analysis. */
export interface PickedImage {
  uri: string;
  base64: string;
  mimeType: string;
  width: number;
  height: number;
  fileSize: number | null;
}

export interface WeatherSnapshot {
  condition?: string;
  temperatureC?: number | null;
  humidityPct?: number | null;
  windSpeedKmh?: number | null;
  fetchedAt?: string;
}

export interface TestModeProvenance {
  active: true;
  code: string;
  display_required: true;
  banner_text: string;
  session_id?: string;
}

/**
 * Whether a diagnosis was confirmed by a trained local classifier or is an
 * OpenAI-vision-only estimate (docs/AI_DECISION_MATRIX.md → DISEASE
 * DETECTION). `null` for controlled-tester reports, which don't carry this
 * provenance and aren't shown through the general-diagnosis screen. The UI
 * must not present these two cases with equal visual confidence.
 */
export type VerificationLevel = 'verified_by_local_model' | 'ai_vision_estimate' | null;

export interface DiseaseReport {
  id: string;
  farmId: string | null;
  crop: string | null;
  cropConfidence: number | null;
  disease: string | null;
  confidence: number | null;
  severity: Severity;
  symptoms: string[];
  causes: string[];
  recommendations: string[];
  prevention: string[];
  conventionalCategoryEnglish: string | null;
  conventionalCategoryTamil: string | null;
  visibleParts: string[];
  needsExpertReview: boolean;
  explanationTamil: string | null;
  explanationEnglish: string | null;
  imageUrl: string | null;
  privateImageAvailable?: boolean;
  modelUsed: string | null;
  testMode: TestModeProvenance | null;
  verificationLevel: VerificationLevel;
  weatherSnapshot: WeatherSnapshot | null;
  latitude: number | null;
  longitude: number | null;
  language: SupportedLanguage;
  createdAt: string;
}

export interface DiseaseReportSummary {
  id: string;
  crop: string | null;
  disease: string | null;
  confidence: number | null;
  severity: Severity;
  imageUrl: string | null;
  privateImageAvailable?: boolean;
  needsExpertReview: boolean;
  testMode: TestModeProvenance | null;
  verificationLevel: VerificationLevel;
  createdAt: string;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiDiseaseReport {
  id: string;
  farm_id: string | null;
  crop: string | null;
  crop_confidence: number | null;
  disease: string | null;
  confidence: number | null;
  severity: Severity;
  symptoms: string[];
  causes: string[];
  recommendations: string[];
  prevention: string[];
  conventional_category_english: string | null;
  conventional_category_tamil: string | null;
  visible_parts: string[];
  needs_expert_review: boolean;
  explanation_tamil: string | null;
  explanation_english: string | null;
  image_url: string | null;
  private_image_available?: boolean;
  thumbnail_url: string | null;
  model_used: string | null;
  test_mode?: TestModeProvenance | null;
  verification_level?: VerificationLevel;
  weather_snapshot: Record<string, unknown> | null;
  latitude: number | null;
  longitude: number | null;
  language: string;
  created_at: string;
}

export interface ApiDiseaseReportSummary {
  id: string;
  crop: string | null;
  disease: string | null;
  confidence: number | null;
  severity: Severity;
  image_url: string | null;
  private_image_available?: boolean;
  needs_expert_review: boolean;
  test_mode?: TestModeProvenance | null;
  verification_level?: VerificationLevel;
  created_at: string;
}
