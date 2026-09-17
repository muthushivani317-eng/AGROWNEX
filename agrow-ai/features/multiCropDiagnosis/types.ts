import type { CropDiagnosisStatus } from "@/config/cropCapabilities";

export type SharedDiagnosisState =
  "accepted" | "uncertain" | "error" | "model_not_available";

export interface ModelNotAvailableResult {
  status: "model_not_available";
  code: "MODEL_NOT_AVAILABLE";
  cropId: string;
  diagnosis: null;
}

export interface CropDiagnosisAdapter {
  cropId: string;
  status: CropDiagnosisStatus;
  predict(input: {
    uri: string;
    mimeType: string;
    cropConfirmed?: boolean;
    cropConfirmationToken?: string;
    farmId?: string;
    kvkSession?: boolean;
    reviewConsent?: boolean;
  }): Promise<ModelNotAvailableResult | CropDiagnosisResult>;
}

export interface CropPredictionResult {
  outcome: "accepted" | "uncertain";
  crop_id: string;
  crop_identity_source: "user_confirmed_not_ai_verified";
  class_id: string | null;
  qualitative_confidence: "low" | "moderate" | "high";
  calibrated_confidence: number;
  margin?: number;
  accepted: boolean;
  official_accuracy_claim: false;
  field_validation_status: "IN_PROGRESS";
  test_mode?: {
    active: true;
    code:
      | "LEGACY_JOINT_CONTROLLED_FIELD_TEST_OVERRIDE"
      | "RESTRICTED_CROP_CONTROLLED_TEST";
    display_required: true;
    banner_text: "TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — RESULT NOT VALIDATED";
    session_id?: string;
  };
  report_id?: string | null;
  review_status?: "pending" | "declined" | null;
  kvk_session?: boolean;
}

export type CropSafetyStatus =
  | "invalid_image"
  | "crop_not_supported"
  | "runtime_not_ready"
  | "field_validation_pending"
  | "farmer_inference_blocked"
  | "pilot_authorization_required"
  | "out_of_domain"
  | "crop_identity_uncertain"
  | "confirmation_replayed"
  | "confirmation_expired"
  | "confirmation_required"
  | "confirmation_mismatch"
  | "tester_role_required"
  | "authorization_unavailable"
  | "release_not_authorized"
  | "model_integrity_failure"
  | "storage_unavailable"
  | "unsupported_image"
  | "low_quality_image"
  | "authentication_required"
  | "throttled"
  | "model_load_failed"
  | "internal_error"
  | "malformed_response"
  | "timeout"
  | "offline"
  | "server_error";

export interface CropSafetyResult {
  outcome: "blocked";
  status: CropSafetyStatus;
  crop_id: string | null;
  message: string;
  diagnosis: null;
}

export type CropDiagnosisResult = CropPredictionResult | CropSafetyResult;
