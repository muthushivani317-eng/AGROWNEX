export type GroundnutPredictionStatus =
  "accepted" | "review_required" | "rejected";

export type GroundnutConfidenceCategory = "HIGH" | "MEDIUM" | "LOW";

export interface GroundnutRankedPrediction {
  class_id: string;
  display_name: string;
  confidence: number;
}

export interface GroundnutImageQuality {
  status: "accepted" | "rejected";
  reasons: string[];
  width: number;
  height: number;
  brightness: number;
  contrast: number;
  blur_score: number;
}

export interface GroundnutPredictionResponse {
  request_id: string;
  crop: "groundnut";
  model_version: "groundnut-efficientnet-b2-v1";
  experimental: true;
  experimental_notice: string;
  status: GroundnutPredictionStatus;
  predicted_disease: GroundnutRankedPrediction | null;
  confidence_category: GroundnutConfidenceCategory | null;
  confidence_score: number | null;
  top_three_predictions: GroundnutRankedPrediction[];
  candidate_prediction: GroundnutRankedPrediction | null;
  image_quality: GroundnutImageQuality;
  rejection_reasons: string[];
  expert_review_required: boolean;
  runtime_device: string;
  processing_time_ms: number;
}

export const GROUNDNUT_TEXT_SYMPTOMS = [
  "dark_leaf_spots",
  "light_leaf_spots",
  "yellow_halo_around_spots",
  "rust_colored_leaf_marks",
  "general_leaf_yellowing",
  "yellowing_between_leaf_veins",
  "leaf_curling",
  "wilting",
  "stunted_growth",
  "holes_or_chewed_edges",
  "uniform_green_leaves",
] as const;

export type GroundnutTextSymptom = (typeof GROUNDNUT_TEXT_SYMPTOMS)[number];

export interface GroundnutTextGuidanceResponse {
  crop: "groundnut";
  status: "preliminary_guidance";
  observed_symptoms: GroundnutTextSymptom[];
  possible_patterns: string[];
  guidance: string;
  expert_review_required: true;
  confirmed_disease: null;
  image_model_confidence: null;
  warnings: string[];
}

export interface GroundnutTranscriptResponse {
  transcript: string;
}

export interface GroundnutTranscriptMapResponse {
  matched_symptoms: GroundnutTextSymptom[];
  unmatched_text: string[];
  ambiguous_text: string[];
}

export type GroundnutDamageExtent = "few" | "several" | "widespread";
export type GroundnutSpreadSpeed = "unknown" | "stable" | "rapid";

export interface GroundnutPestObservationResponse {
  observation_id: string;
  crop: "groundnut";
  status: "pending_expert_review";
  damage_extent: GroundnutDamageExtent;
  spread_speed: GroundnutSpreadSpeed;
  consent: true;
  private_photo_stored: true;
  pest_label: null;
  diagnosis: null;
}
